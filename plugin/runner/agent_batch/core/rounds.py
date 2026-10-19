"""A branch's review rounds, and when a new finding stops holding its pull request back."""

from __future__ import annotations

import textwrap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from agent_batch.core.model import Finding, FoundIssue, ReviewResult
from agent_batch.core.results import to_findings

# From this review of a branch on, a new medium finding goes in the PR's follow-up issue instead
# of blocking (SPEC §4.5).
CONVERGES_FROM = 3
TITLE_WIDTH = 72


@dataclass(frozen=True)
class Round:
    """One review of a branch: its place in the order, the commit it read, what it found and
    whether it approved the branch."""

    number: int
    head: str
    findings: tuple[Finding, ...]
    approved: bool = False


def earlier(records: Iterable[Mapping[str, object]], branch: str) -> tuple[Round, ...]:
    """The reviews of `branch` that the event log kept, oldest first."""
    rounds: list[Round] = []
    for record in records:
        head = record.get("head")
        findings = to_findings(record.get("findings"))
        # Reviews logged before #74 kept only how many findings they had, and no branch.
        if record.get("branch") != branch or not isinstance(head, str) or findings is None:
            continue
        approved = record.get("approved") is True
        rounds.append(Round(len(rounds) + 1, head, findings, approved))
    return tuple(rounds)


def approved_findings(earlier: Iterable[Round], head: str) -> tuple[Finding, ...] | None:
    """The findings the PR's body keeps from an approved review of `head`, if one read it.

    They leave out what that review filed in the follow-up, as they did when it ran.
    """
    for review in earlier:
        if review.approved and review.head == head:
            kept, _ = settle(ReviewResult(approved=True, findings=review.findings), review.number)
            return kept.findings
    return None


def filed(finding: Finding, number: int) -> bool:
    """Whether review `number` of a branch files this finding in the follow-up rather than block."""
    return number >= CONVERGES_FROM and finding.severity == "medium" and finding.origin == "new"


def settle(review: ReviewResult, number: int) -> tuple[ReviewResult, tuple[Finding, ...]]:
    """The review the runner acts on, and the findings it files in the PR's follow-up instead."""
    to_file = tuple(finding for finding in review.findings if filed(finding, number))
    if not to_file:
        return review, ()
    kept = tuple(finding for finding in review.findings if not filed(finding, number))
    blocks = any(finding.severity != "low" for finding in kept)
    return ReviewResult(approved=review.approved or not blocks, findings=kept), to_file


def found_issue(finding: Finding, number: int) -> FoundIssue:
    """A finding review `number` filed, as one item of the PR's follow-up issue (SPEC §4.5)."""
    title = textwrap.shorten(finding.problem, TITLE_WIDTH, placeholder="…")
    body = (
        f"Review {number} of the branch found this at `{finding.location}`. From review "
        f"{CONVERGES_FROM} of a branch on, a new medium finding doesn't block its pull request: "
        f"it goes in the follow-up issue instead (SPEC §5).\n\n{finding.problem}\n\n"
        f"**Suggestion:** {finding.suggestion}"
    )
    return FoundIssue("bug", title or f"A review finding at {finding.location}", body)
