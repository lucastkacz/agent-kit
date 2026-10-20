"""A published PR, from its risk to its merge, through one conflict's resolution (SPEC §11.1)."""

from __future__ import annotations

import time

from agent_batch.context import Context, Lane
from agent_batch.core import merge, progress, prompts, results, risk
from agent_batch.core.config import HIGH_RISK
from agent_batch.core.merge import MergeStatus
from agent_batch.core.model import Outcome, Risk
from agent_batch.job import (
    Job,
    Stopped,
    checked,
    ended,
    pr_of,
    pr_text,
    require_committed,
    review_once,
    watched,
)
from agent_batch.shell import retry
from agent_batch.shell.proc import CommandError

RISK_PATHS = ".claude/risk-paths"


def route(ctx: Context, lane: Lane, job: Job) -> Outcome:
    ctx.status.step(lane.index, progress.RISK_AND_MERGE)
    level = classify(ctx, lane, job)
    if level.high:
        hold(ctx, pr_of(job), level)
        ctx.events.emit("waiting_owner", lane=lane.index, issue=job.issue.number, pr=pr_of(job))
        return Outcome.WAITING_OWNER
    return _merge(ctx, lane, job, resolve_conflicts=True)


def classify(ctx: Context, lane: Lane, job: Job) -> Risk:
    # The project's risk paths come from the base branch, where no agent of this batch wrote.
    patterns = risk.parse_patterns(ctx.git.base_file(lane.worktree, RISK_PATHS) or "")
    return risk.classify(ctx.git.changed_files(lane.worktree), patterns, job.issue)


def hold(ctx: Context, pr: int, level: Risk) -> None:
    """Leaves a high-risk PR for the owner to merge, saying why."""
    wait = ctx.config.poll_seconds
    retry.retried(lambda: ctx.gh.pr_add_label(pr, HIGH_RISK), wait)
    reasons = "\n".join(f"- {reason}" for reason in level.reasons)
    text = f"**High risk: the owner merges this PR.**\n\n{reasons}\n"
    retry.retried_with(
        lambda: ctx.gh.pr_comment(pr, text),
        lambda: ctx.gh.pr_comment_unless_posted(pr, text),
        wait,
    )


def _merge(ctx: Context, lane: Lane, job: Job, *, resolve_conflicts: bool) -> Outcome:
    # Again on the merge after a conflict, which went through a review and the PR in between.
    ctx.status.step(lane.index, progress.RISK_AND_MERGE)
    pr = pr_of(job)
    head = ctx.git.head(lane.worktree)
    retry.retried(lambda: ctx.gh.arm_merge(pr, head), ctx.config.poll_seconds)
    ctx.events.emit("merge_armed", lane=lane.index, issue=job.issue.number, pr=pr)
    status = _wait(ctx, pr)
    if status is MergeStatus.MERGED:
        ctx.events.emit("merged", lane=lane.index, issue=job.issue.number, pr=pr)
        _finish(ctx, lane, job)
        return Outcome.MERGED
    if status is MergeStatus.CONFLICT and resolve_conflicts:
        _resolve(ctx, lane, job)
        return _merge(ctx, lane, job, resolve_conflicts=False)
    raise Stopped(Outcome.BLOCKED, f"PR #{pr} didn't merge: {status.value}.")


def _finish(ctx: Context, lane: Lane, job: Job) -> None:
    """Leaves the merged branch; a failure only goes to the log, since the issue is done."""
    try:
        ctx.git.finish_branch(lane.worktree, job.branch)
    except CommandError as error:
        ctx.events.emit(
            "cleanup_failed", lane=lane.index, issue=job.issue.number, detail=str(error)
        )


def _wait(ctx: Context, pr: int) -> MergeStatus:
    deadline = time.monotonic() + ctx.config.merge_timeout
    while True:
        status = merge.decide(retry.retried(lambda: ctx.gh.pr_state(pr), ctx.config.poll_seconds))
        if status is not MergeStatus.WAIT:
            return status
        if time.monotonic() >= deadline:
            return MergeStatus.TIMED_OUT
        time.sleep(ctx.config.poll_seconds)


def _resolve(ctx: Context, lane: Lane, job: Job) -> None:
    """One attempt at the conflicts with the base branch, then a new review (SPEC §11.1)."""
    upstream = ctx.config.upstream
    conflicts = ctx.git.merge_upstream(lane.worktree)
    if conflicts:
        prompt = prompts.resolve(job.issue.number, upstream, conflicts)
        run = watched(ctx, lane).resolve(lane.worktree, prompt)
        ended(ctx, lane, job.issue.number, "resolve", run)
        answer = results.to_resolve(checked(ctx, lane, run, job.report, "conflict resolution"))
        if answer is None or not answer.resolved:
            reason = answer.message if answer is not None else "its answer doesn't match its schema"
            raise Stopped(
                Outcome.BLOCKED, f"The conflicts with {upstream} weren't resolved: {reason}"
            )
        require_committed(ctx, lane)
    job.report.review_rounds += 1
    review = review_once(ctx, lane, job)
    if not review.approved:
        raise Stopped(
            Outcome.BLOCKED, "The review asked for changes after the conflicts were resolved."
        )
    job.findings = review.findings
    retry.retried(lambda: ctx.git.push(lane.worktree, job.branch), ctx.config.poll_seconds)
    title, body = pr_text(job)
    pr = pr_of(job)
    retry.retried(lambda: ctx.gh.edit_pr(pr, title, body), ctx.config.poll_seconds)
