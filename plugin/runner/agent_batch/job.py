"""An issue's job, and the steps that both its first pass and its merge take (SPEC §5)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agent_batch import filing
from agent_batch.context import Context, Lane
from agent_batch.core import naming, progress, prompts, results, rounds
from agent_batch.core.model import (
    ClaudeRun,
    EndedKind,
    Finding,
    ImplementResult,
    Issue,
    IssueReport,
    Outcome,
    ReviewResult,
    RunDenial,
    RunKind,
)
from agent_batch.shell.claude import Claude


class Stopped(Exception):
    """The issue can't go on; `outcome` says how it ended."""

    def __init__(self, outcome: Outcome, detail: str) -> None:
        super().__init__(detail)
        self.outcome = outcome
        self.detail = detail


@dataclass
class Job:
    issue: Issue
    branch: str
    report: IssueReport
    work: ImplementResult | None = None
    # The approved review's findings, which go into the PR's body.
    findings: tuple[Finding, ...] = ()


def watched(ctx: Context, lane: Lane) -> Claude:
    """The runs, each of whose tool uses becomes the lane's last action as it goes (#107).

    Their tokens add to the lane's estimated cost as they go, too (#144).
    """
    return ctx.claude.watching(
        lambda action: ctx.status.act(lane.index, action, ctx.clock()),
        lambda tokens: ctx.status.used(lane.index, tokens),
    )


def ended(ctx: Context, lane: Lane, issue: int, kind: EndedKind, run: ClaudeRun) -> None:
    """Logs what the run cost and its tokens, which price a resumed batch's runs (#217)."""
    ctx.events.emit(
        "run_ended",
        lane=lane.index,
        issue=issue,
        kind=kind,
        cost_usd=run.cost_usd,
        tokens=run.tokens,
    )


def checked(
    ctx: Context, lane: Lane, run: ClaudeRun, report: IssueReport, what: RunKind
) -> dict[str, object]:
    for denial in run.denials:
        report.denials.append(RunDenial(what, denial))
        ctx.events.emit(
            "permission_denied",
            issue=report.number,
            run=what,
            session=denial.session,
            tool=denial.tool,
            input=denial.tool_input,
        )
    report.cost_usd += run.cost_usd
    ctx.status.spent(lane.index, report.cost_usd)
    if run.limit_reached:
        raise Stopped(Outcome.INTERRUPTED, "the subscription's usage limit was reached")
    if run.error is not None or run.data is None:
        raise Stopped(Outcome.FAILED, f"the {what} run failed: {run.error}")
    return run.data


def require_committed(ctx: Context, lane: Lane) -> None:
    if not ctx.git.is_clean(lane.worktree):
        raise Stopped(Outcome.FAILED, "the branch has uncommitted changes")
    if ctx.git.commits_ahead(lane.worktree) == 0:
        raise Stopped(Outcome.FAILED, "the branch has no commits of its own")


def review_once(ctx: Context, lane: Lane, job: Job) -> ReviewResult:
    """One review of the branch, which gets what its earlier reviews found (SPEC §5)."""
    earlier = rounds.earlier(ctx.events.project_records("reviewed"), job.branch)
    number = len(earlier) + 1
    head = ctx.git.head(lane.worktree)
    ctx.status.step(lane.index, progress.REVIEW, job.report.review_rounds)
    started = ctx.clock()
    run = watched(ctx, lane).review(lane.worktree, prompts.review(job.issue.number, earlier))
    seconds = ctx.clock() - started
    answer = results.to_review(checked(ctx, lane, run, job.report, "review"))
    if answer is None:
        raise Stopped(Outcome.FAILED, "the reviewer's answer doesn't match its schema")
    review, filed = rounds.settle(answer, number)
    # The issue goes before the event: if filing fails, this round isn't logged and runs again.
    # That can file a finding twice, but the next round never reads as filed one that wasn't.
    found = [rounds.found_issue(finding, number) for finding in filed]
    filing.file(ctx, job.issue.number, job.branch, found)
    # Every finding, filed ones included, so that the next review can read what this one found.
    # Its cost and time too: `ship`'s reviews count in no summary, only in the acceptance's numbers.
    # Its tokens price a resumed batch's runs before any of its own has ended (#156).
    ctx.events.emit(
        "reviewed",
        lane=lane.index,
        issue=job.issue.number,
        branch=job.branch,
        head=head,
        round=number,
        approved=review.approved,
        findings=[asdict(finding) for finding in answer.findings],
        cost_usd=run.cost_usd,
        tokens=run.tokens,
        seconds=round(seconds, 1),
    )
    return review


def work(job: Job) -> ImplementResult:
    if job.work is None:
        raise Stopped(Outcome.FAILED, "there's no implementation to publish")
    return job.work


def pr_text(job: Job) -> tuple[str, str]:
    """The PR's title and body: the implementer's, with the approved review's findings."""
    done = work(job)
    title = naming.pr_title(done.title, job.issue)
    return title, naming.pr_body(done.pr_body, job.issue.number, job.findings)


def pr_of(job: Job) -> int:
    if job.report.pr is None:
        raise Stopped(Outcome.FAILED, "the issue has no PR")
    return job.report.pr
