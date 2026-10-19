"""A pull request's follow-up issue: the work found along the way, in one place (SPEC §4.5)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from agent_batch.core.model import FoundIssue, IssueKind

# The kinds of found work, the most severe first.
SEVERITY: tuple[IssueKind, ...] = ("bug", "task", "idea")


def label(items: Sequence[FoundIssue]) -> IssueKind:
    """The most severe kind among the items: a bug over a task over an idea."""
    return _most_severe(item.kind for item in items)


def issue(items: Sequence[FoundIssue], number: int) -> FoundIssue:
    """The issue that opens issue `number`'s follow-ups: one item as it came, several together."""
    if len(items) == 1:
        [only] = items
        return FoundIssue(only.kind, only.title, f"{only.body.rstrip()}\n\n{_footer(number)}")
    return FoundIssue(label(items), f"Follow-ups of #{number}", comment(items, number))


def comment(items: Sequence[FoundIssue], number: int) -> str:
    """Each item as its own section, with its kind, title and body, then where it was found."""
    sections = [
        f"## {item.kind.capitalize()}: {item.title}\n\n{item.body.rstrip()}" for item in items
    ]
    return "\n\n".join([*sections, _footer(number)])


def existing(records: Iterable[Mapping[str, object]], branch: str) -> int | None:
    """The follow-up issue that the `issue_found` events name for the branch's PR, if any."""
    filed = [record.get("found") for record in records if record.get("branch") == branch]
    numbers = [number for number in filed if isinstance(number, int)]
    return numbers[-1] if numbers else None


def relabel(
    labels: Iterable[str], items: Sequence[FoundIssue]
) -> tuple[IssueKind, frozenset[str]] | None:
    """The kind label to add to a follow-up issue that gets new items, and those to remove.

    None when its label is already the most severe kind among its old and new items.
    """
    kinds = frozenset(name for name in labels if name in SEVERITY)
    wanted = _most_severe([*kinds, *(item.kind for item in items)])
    if wanted in kinds:
        return None
    return wanted, kinds


def _most_severe(kinds: Iterable[str]) -> IssueKind:
    present = set(kinds)
    for kind in SEVERITY:
        if kind in present:
            return kind
    raise ValueError("A follow-up issue needs at least one item of found work to take a label.")


def _footer(number: int) -> str:
    return f"Found while working on #{number}."
