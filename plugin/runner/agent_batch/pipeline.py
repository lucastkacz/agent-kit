"""One issue, from its branch to its merge (SPEC §5)."""

from __future__ import annotations

from agent_batch import filing, landing
from agent_batch.context import Context, Lane
from agent_batch.core import eligibility, naming, progress, prompts, results, risk, rounds
from agent_batch.core.config import BLOCKED, HIGH_RISK
from agent_batch.core.model import ClaudeRun, EndedKind, Finding, Issue, IssueReport, Outcome
from agent_batch.job import (
    Job,
    Stopped,
    checked,
    ended,
    pr_text,
    require_committed,
    review_once,
    watched,
    work,
)
from agent_batch.shell import retry
from agent_batch.shell.proc import CommandError

# GitHub's reason for an issue that its PR closed; "NOT_PLANNED" means the work was dropped.
CLOSED_AS_COMPLETED = "COMPLETED"


def run_issue(ctx: Context, lane: Lane, number: int) -> IssueReport:
    started = ctx.clock()
    report = IssueReport(number=number, outcome=Outcome.FAILED)
    try:
        report.outcome = _attempt(ctx, lane, number, report)
    except Stopped as stop:
        report.outcome, report.detail = stop.outcome, stop.detail
    except CommandError as error:
        report.outcome, report.detail = Outcome.FAILED, str(error)
    report.seconds = ctx.clock() - started
    announce(ctx, report)
    ctx.events.emit(
        "issue_finished",
        lane=lane.index,
        issue=number,
        outcome=report.outcome.value,
        detail=report.detail,
    )
    return report


def _attempt(ctx: Context, lane: Lane, number: int, report: IssueReport) -> Outcome:
    issue = ctx.gh.issue(number)
    if _merged_before(ctx, issue, report):
        return Outcome.MERGED
    refusal = eligibility.refusal(issue, ctx.owner)
    if refusal is not None:
        raise Stopped(Outcome.SKIPPED, refusal)
    report.human_checks = risk.count_human_checks(issue.body)
    job = Job(issue=issue, branch=naming.branch_name(issue), report=report)
    if _waiting_before(ctx, job):
        return Outcome.WAITING_OWNER
    ctx.git.start_branch(lane.worktree, job.branch)
    ctx.events.emit("issue_started", lane=lane.index, issue=number, branch=job.branch)
    state = progress.LaneState(
        number, progress.IMPLEMENTATION, ctx.clock(), ctx.config.review_rounds
    )
    ctx.status.start(lane.index, state)
    _start_work(ctx, lane, job)
    review_until_approved(ctx, lane, job)
    publish(ctx, lane, job)
    return landing.route(ctx, lane, job)


def _merged_before(ctx: Context, issue: Issue, report: IssueReport) -> bool:
    """Whether a merged PR closed the issue, as in an earlier run, so a re-run goes on past it."""
    if issue.state == "OPEN":
        return False
    closure = ctx.gh.closure(issue.number)
    if closure.reason != CLOSED_AS_COMPLETED:
        return False
    merged = [pr for pr in closure.prs if ctx.gh.pr_state(pr).state == "MERGED"]
    if not merged:
        return False
    report.pr, report.detail = merged[0], "it merged in an earlier run"
    report.human_checks = risk.count_human_checks(issue.body)
    return True


def _waiting_before(ctx: Context, job: Job) -> bool:
    """Whether an earlier run left the issue's PR to the owner, so a re-run doesn't redo it."""
    pr = ctx.gh.find_pr(job.branch, HIGH_RISK)
    if pr is None:
        return False
    job.report.pr, job.report.detail = pr, "its PR has waited for the owner since an earlier run"
    return True


def _start_work(ctx: Context, lane: Lane, job: Job) -> None:
    reuse = lane.session_id is not None and lane.session_issues < ctx.config.issues_per_session
    prompt = prompts.implement(job.issue.number)
    run = watched(ctx, lane).implement(lane.worktree, prompt, lane.session_id if reuse else None)
    lane.session_issues = lane.session_issues + 1 if reuse else 1
    lane.session_id = run.session_id
    _accept_work(ctx, lane, job, run, "implementation")


def _accept_work(ctx: Context, lane: Lane, job: Job, run: ClaudeRun, kind: EndedKind) -> None:
    ended(ctx, lane, job.issue.number, kind, run)
    answer = results.to_implement(checked(ctx, lane, run, job.report, "implementation"))
    if answer is None:
        raise Stopped(Outcome.FAILED, "the implementer's answer doesn't match its schema")
    if answer.status == "blocked":
        raise Stopped(Outcome.BLOCKED, answer.message)
    if answer.status == "failed":
        raise Stopped(Outcome.FAILED, answer.message)
    require_committed(ctx, lane)
    job.work = answer


def review_until_approved(ctx: Context, lane: Lane, job: Job) -> None:
    """Reviews, sends findings back to the implementer, and gives up after the last round.

    An approval's findings go back once per branch too, the low pass, so that the PR reaches the
    owner with its lows fixed or answered; it isn't a round that asked for changes (SPEC §5).
    """
    if _approved_before(ctx, lane, job):
        return
    most = ctx.config.review_rounds
    asked = 0
    low_passed = rounds.low_passed(ctx.events.project_records("low_pass"), job.branch)
    while True:
        job.report.review_rounds += 1
        review = review_once(ctx, lane, job)
        if review.approved and (low_passed or not review.findings):
            job.findings = review.findings
            return
        if review.approved:
            low_passed = True
            head = ctx.git.head(lane.worktree)
            ctx.events.emit(
                "low_pass", lane=lane.index, issue=job.issue.number, branch=job.branch, head=head
            )
        else:
            asked += 1
            if asked == most:
                findings = prompts.findings_list(review.findings)
                raise Stopped(
                    Outcome.BLOCKED,
                    f"The review still asks for changes after {most} rounds:\n\n{findings}",
                )
        _send_back(ctx, lane, job, review.findings)


def _send_back(ctx: Context, lane: Lane, job: Job, findings: tuple[Finding, ...]) -> None:
    """Has the implementer's session fix or answer a review's findings."""
    prompt = prompts.fix(job.issue.number, findings)
    ctx.status.step(lane.index, progress.IMPLEMENTATION)
    run = watched(ctx, lane).implement(lane.worktree, prompt, lane.session_id)
    lane.session_id = run.session_id or lane.session_id
    _accept_work(ctx, lane, job, run, "fix")


def _approved_before(ctx: Context, lane: Lane, job: Job) -> bool:
    """Whether an approved review already read the branch's head, as before a failed push."""
    earlier = rounds.earlier(ctx.events.project_records("reviewed"), job.branch)
    head = ctx.git.head(lane.worktree)
    findings = rounds.approved_findings(earlier, head)
    if findings is None:
        return False
    job.findings = findings
    # Says why this run reviewed nothing, which its summary's 0 rounds don't (#210).
    ctx.events.emit(
        "review_reused", lane=lane.index, issue=job.issue.number, branch=job.branch, head=head
    )
    return True


def publish(ctx: Context, lane: Lane, job: Job) -> int:
    """Pushes the branch, opens or updates its PR and files the work found along the way."""
    done = work(job)
    ctx.status.step(lane.index, progress.PULL_REQUEST)
    wait = ctx.config.poll_seconds
    retry.retried(lambda: ctx.git.push(lane.worktree, job.branch), wait)
    title, body = pr_text(job)
    base = ctx.config.base_branch
    pr, opened = retry.retried(lambda: ctx.gh.open_pr(job.branch, base, title, body), wait)
    if opened:
        ctx.events.emit("pr_opened", lane=lane.index, issue=job.issue.number, pr=pr)
    else:
        retry.retried(lambda: ctx.gh.edit_pr(pr, title, body), wait)
        ctx.events.emit("pr_updated", lane=lane.index, issue=job.issue.number, pr=pr)
    job.report.pr = pr
    filing.file(ctx, job.issue.number, job.branch, done.found)
    return pr


def announce(ctx: Context, report: IssueReport) -> None:
    """Writes a blocked or failed issue's question on GitHub, where the owner will see it."""
    if report.outcome not in (Outcome.BLOCKED, Outcome.FAILED):
        return
    if report.outcome is Outcome.BLOCKED:
        heading = "**Blocked: this needs a decision from the owner.**"
    else:
        heading = "**The batch couldn't finish this issue.**"
    body = (
        f"{heading}\n\n{report.detail}\n\nOnce it's settled, remove the `{BLOCKED}` label and the "
        "issue goes back to the next batch.\n"
    )
    try:
        wait = ctx.config.poll_seconds
        retry.retried(lambda: ctx.gh.add_label(report.number, BLOCKED), wait)
        # A 5xx after GitHub saved the comment posts it twice: better than no comment at all.
        retry.retried(lambda: ctx.gh.comment(report.number, body), wait)
        # A lane's set-aside reports start out unannounced; this one now has its comment.
        report.unannounced = False
    except CommandError as error:
        report.unannounced = True
        ctx.events.emit("announce_failed", issue=report.number, detail=str(error))
