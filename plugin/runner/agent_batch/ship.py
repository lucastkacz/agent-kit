"""Direct mode: review the current branch, open its PR and arm its merge (SPEC §3.4)."""

from __future__ import annotations

import sys
from pathlib import Path

from agent_batch.context import Context, Lane
from agent_batch.core import eligibility, prompts
from agent_batch.core.model import ImplementResult, IssueReport, Outcome
from agent_batch.pipeline import (
    Job,
    Stopped,
    classify,
    hold,
    publish,
    require_committed,
    review_once,
)

CHANGES_REQUESTED = 2


class ShipError(RuntimeError):
    """The branch can't be shipped as it is."""


def ship(ctx: Context, cwd: Path, number: int, title: str, body: str) -> int:
    issue = ctx.gh.issue(number)
    refusal = eligibility.refusal(issue, ctx.owner)
    if refusal is not None:
        raise ShipError(f"#{number} can't be shipped: {refusal}")
    lane = Lane(index=0, worktree=ctx.git.toplevel(cwd))
    branch = ctx.git.current_branch(lane.worktree)
    if not branch.startswith(f"{number}-"):
        raise ShipError(f"ship #{number} from a branch named {number}-<short-name>, not {branch!r}")
    work = ImplementResult("done", title, body, "", ())
    job = Job(issue, branch, IssueReport(number, Outcome.FAILED), work)
    try:
        return _ship(ctx, lane, job)
    except Stopped as stop:
        raise ShipError(stop.detail) from stop


def _ship(ctx: Context, lane: Lane, job: Job) -> int:
    # The review and the risk compare the branch with the base, which may have moved on.
    ctx.git.fetch(lane.worktree)
    require_committed(ctx, lane)
    review = review_once(ctx, lane, job)
    if not review.approved:
        sys.stdout.write("The review asks for changes:\n\n")
        sys.stdout.write(prompts.findings_list(review.findings) + "\n")
        return CHANGES_REQUESTED
    pr = publish(ctx, lane, job)
    level = classify(ctx, lane, job)
    if level.high:
        hold(ctx, pr, level)
        outcome = Outcome.WAITING_OWNER
    else:
        ctx.gh.arm_merge(pr, ctx.git.head(lane.worktree))
        outcome = Outcome.ARMED
    ctx.events.emit("shipped", issue=job.issue.number, pr=pr, outcome=outcome.value)
    return 0
