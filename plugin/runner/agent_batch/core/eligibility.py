"""Whether an issue is work an agent may take (SPEC §4.4 and §10.6)."""

from __future__ import annotations

from agent_batch.core.config import BLOCKED, READY
from agent_batch.core.model import Issue
from agent_batch.core.risk import stated_risk


def refusal(issue: Issue, owner: str) -> str | None:
    """Why the issue can't be taken, or None when it can."""
    if issue.state != "OPEN":
        return "the issue is closed"
    if issue.author != owner:
        return f"it was opened by {issue.author}, not by the owner"
    if READY not in issue.labels:
        return f"it isn't labeled {READY}"
    if BLOCKED in issue.labels:
        return f"it's labeled {BLOCKED}"
    if stated_risk(issue.body) is None:
        return "it doesn't state its risk"
    return None
