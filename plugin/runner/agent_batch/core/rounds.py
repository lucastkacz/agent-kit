"""A branch's review rounds, and when a new finding stops holding its pull request back."""

from __future__ import annotations

import textwrap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from agent_batch.core.model import Finding, FoundIssue, ReviewResult
from agent_batch.core.results import to_findings

# From this review of a branch on, a new medium finding is filed as an issue instead of blocking.
CONVERGES_FROM = 3
TITLE_WIDTH = 72


@dataclass(frozen=True)
class Round:
    """One review of a branch: its place in the order, the commit it read and what it found."""

    number: int
    head: str
    findings: tuple[Finding, ...]


def earlier(records: Iterable[Mapping[str, object]], branch: str) -> tuple[Round, ...]:
    """The reviews of `branch` that the event log kept, oldest first."""
    rounds: list[Round] = []
    for record in records:
        head = record.get("head")
        findings = to_findings(record.get("findings"))
        # Reviews logged before #74 kept only how many findings they had, and no branch.
        if record.get("branch") != branch or not isinstance(head, str) or findings is None:
            continue
        rounds.append(Round(len(rounds) + 1, head, findings))
    return tuple(rounds)


def filed(finding: Finding, number: int) -> bool:
    """Whether review `number` of a branch files this finding as an issue rather than block."""
    return number >= CONVERGES_FROM and finding.severity == "medium" and finding.origin == "new"


def settle(review: ReviewResult, number: int) -> tuple[ReviewResult, tuple[Finding, ...]]:
    """The review the runner acts on, and the findings it files as issues instead."""
    to_file = tuple(finding for finding in review.findings if filed(finding, number))
    if not to_file:
        return review, ()
    kept = tuple(finding for finding in review.findings if not filed(finding, number))
    blocks = any(finding.severity != "low" for finding in kept)
    return ReviewResult(approved=review.approved or not blocks, findings=kept), to_file


def found_issue(finding: Finding, number: int) -> FoundIssue:
    """The issue that waits for a finding review `number` filed, like work found along the way."""
    title = textwrap.shorten(finding.problem, TITLE_WIDTH, placeholder="…")
    body = (
        f"Review {number} of the branch found this at `{finding.location}`. From review "
        f"{CONVERGES_FROM} of a branch on, a new medium finding doesn't block its pull request: "
        f"it waits here instead (SPEC §5).\n\n{finding.problem}\n\n"
        f"**Suggestion:** {finding.suggestion}"
    )
    return FoundIssue("bug", title or f"A review finding at {finding.location}", body)
