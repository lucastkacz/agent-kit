"""Direct mode: review the current branch, open its PR and arm its merge (SPEC §3.4)."""

from __future__ import annotations

import sys
from pathlib import Path

from agent_batch.context import Context, Lane
from agent_batch.core import eligibility, naming, progress, prompts
from agent_batch.core.model import ImplementResult, IssueReport, Outcome
from agent_batch.job import Job, Stopped, require_committed, review_once
from agent_batch.landing import classify, hold
from agent_batch.pipeline import publish

CHANGES_REQUESTED = 2


class ShipError(RuntimeError):
    """The branch can't be shipped as it is."""


def ship(ctx: Context, cwd: Path, number: int, title: str, body: str) -> int:
    # Refused before the review: `publish` would fall back to the issue's title, cut mid-phrase,
    # and a caller of `ship` can fix the flag, unlike a lane's implementer.
    if (wrong := naming.title_refusal(title)) is not None:
        raise ShipError(
            f"{title!r} can't be the PR's title: {wrong}. Ship again with a Conventional Commits "
            f"title of at most {naming.MAX_TITLE} characters, such as 'feat: export the cards'"
        )
    issue = ctx.gh.issue(number)
    refusal = eligibility.refusal(issue, ctx.owner)
    if refusal is not None:
        raise ShipError(f"#{number} can't be shipped: {refusal}")
    lane = Lane(index=0, worktree=ctx.git.toplevel(cwd))
    branch = ctx.git.current_branch(lane.worktree)
    if not branch.startswith(f"{number}-"):
        raise ShipError(f"ship #{number} from a branch named {number}-<short-name>, not {branch!r}")
    work = ImplementResult("done", title, body, "", ())
    # `ship` runs one review round, and starts at the pipeline's review (SPEC §5).
    report = IssueReport(number, Outcome.FAILED, review_rounds=1)
    job = Job(issue, branch, report, work)
    ctx.status.start(lane.index, progress.LaneState(number, progress.REVIEW, ctx.clock(), 1))
    try:
        return _ship(ctx, lane, job)
    except Stopped as stop:
        raise ShipError(stop.detail) from stop
    finally:
        ctx.status.drop(lane.index)
        ctx.status.close()


def _ship(ctx: Context, lane: Lane, job: Job) -> int:
    # The review and the risk compare the branch with the base, which may have moved on.
    ctx.git.fetch(lane.worktree)
    require_committed(ctx, lane)
    review = review_once(ctx, lane, job)
    if not review.approved:
        sys.stdout.write("The review asks for changes:\n\n")
        sys.stdout.write(prompts.findings_list(review.findings) + "\n")
        return CHANGES_REQUESTED
    job.findings = review.findings
    pr = publish(ctx, lane, job)
    ctx.status.step(lane.index, progress.RISK_AND_MERGE)
    level = classify(ctx, lane, job)
    if level.high:
        hold(ctx, pr, level)
        outcome = Outcome.WAITING_OWNER
    else:
        ctx.gh.arm_merge(pr, ctx.git.head(lane.worktree))
        outcome = Outcome.ARMED
    ctx.events.emit("shipped", issue=job.issue.number, pr=pr, outcome=outcome.value)
    return 0
