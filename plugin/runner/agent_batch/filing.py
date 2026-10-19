"""Files the work found along the way in a PR's one follow-up issue (SPEC §4.5)."""

from __future__ import annotations

from collections.abc import Sequence

from agent_batch.context import Context
from agent_batch.core import followup
from agent_batch.core.model import FoundIssue


def file(ctx: Context, number: int, branch: str, items: Sequence[FoundIssue]) -> None:
    """Files issue `number`'s found work: the first items open the branch's follow-up issue.

    Later ones, from a later review, join it as a comment, found again from the event log,
    while it's open. Planning closes it once it folds it into its issues, so a closed one
    gets a new follow-up issue: a comment on it would track nothing.
    """
    if not items:
        return
    known = followup.existing(ctx.events.project_records("issue_found"), branch)
    current = ctx.gh.issue(known) if known is not None else None
    if known is None or current is None or current.state != "OPEN":
        found = followup.issue(items, number)
        filed = ctx.gh.create_issue(found.title, found.body, found.kind)
        ctx.events.emit("issue_found", issue=number, branch=branch, found=filed)
        return
    ctx.gh.comment(known, followup.comment(items, number))
    change = followup.relabel(current.labels, items)
    if change is not None:
        ctx.gh.relabel(known, *change)
