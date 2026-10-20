"""Direct mode: review the current branch, open its PR and arm its merge (SPEC §3.4)."""

from __future__ import annotations

import sys
from pathlib import Path

from agent_batch.context import Context, Lane
from agent_batch.core import eligibility, naming, progress, prompts
from agent_batch.core.model import ImplementResult, Issue, IssueReport, Outcome
from agent_batch.job import Job, Stopped, require_committed, review_once
from agent_batch.landing import classify, hold
from agent_batch.pipeline import publish

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
    # `ship` runs one review round, and starts at the pipeline's review (SPEC §5).
    report = IssueReport(number, Outcome.FAILED, review_rounds=1)
    job = Job(issue, branch, report, work)
    ctx.status.start(lane.index, progress.LaneState(number, progress.REVIEW, ctx.clock(), 1))
    try:
        return _ship(ctx, lane, job, title)
    except Stopped as stop:
        raise ShipError(stop.detail) from stop
    finally:
        ctx.status.drop(lane.index)


def _ship(ctx: Context, lane: Lane, job: Job, title: str) -> int:
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
    _explain_title(title, job.issue)
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


def _explain_title(given: str, issue: Issue) -> None:
    """Says why the PR didn't get the given title, since `publish` falls back to the issue's."""
    refusal = naming.title_refusal(given)
    if refusal is None:
        return
    used = naming.pr_title(given, issue)
    sys.stdout.write(
        f"The PR's title is {used!r}, not {given!r}: {refusal}. To use another, ship again "
        f"with a Conventional Commits title of at most {naming.MAX_TITLE} characters.\n"
    )
