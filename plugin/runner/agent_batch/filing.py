"""Files the work found along the way in a PR's one follow-up issue (SPEC §4.5)."""

from __future__ import annotations

from collections.abc import Sequence

from agent_batch.context import Context
from agent_batch.core import followup
from agent_batch.core.model import FoundIssue, Issue
from agent_batch.shell import retry


def file(ctx: Context, number: int, branch: str, items: Sequence[FoundIssue]) -> None:
    """Files issue `number`'s found work: the first items open the branch's follow-up issue.

    Later ones, from a later review, join it as a comment, found again from the event log,
    while it's open. Planning closes it once it folds it into its issues, so a closed one
    gets a new follow-up issue: a comment on it would track nothing.
    """
    if not items:
        return
    wait = ctx.config.poll_seconds
    known = followup.existing(ctx.events.project_records("issue_found"), branch)
    current = retry.retried(lambda: ctx.gh.issue(known), wait) if known is not None else None
    if current is None or current.state != "OPEN":
        found = followup.issue(items, number)
        filed = retry.retried_with(
            lambda: ctx.gh.create_issue(found.title, found.body, found.kind),
            lambda: ctx.gh.create_issue_unless_created(found.title, found.body, found.kind),
            wait,
        )
        ctx.events.emit("issue_found", issue=number, branch=branch, found=filed)
        return
    _join(ctx, current, number, items)


def _join(ctx: Context, follow_up: Issue, number: int, items: Sequence[FoundIssue]) -> None:
    """Comments the items on the open follow-up issue and relabels it, tried again as #210's."""
    wait = ctx.config.poll_seconds
    text = followup.comment(items, number)
    change = followup.relabel(follow_up.labels, items)
    retry.retried_with(
        lambda: ctx.gh.comment(follow_up.number, text),
        lambda: ctx.gh.comment_unless_posted(follow_up.number, text),
        wait,
    )
    if change is not None:
        retry.retried(lambda: ctx.gh.relabel(follow_up.number, *change), wait)
