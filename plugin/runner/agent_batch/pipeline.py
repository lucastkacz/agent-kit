"""One issue, from its branch to its merge (SPEC §5)."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

from agent_batch.context import Context, Lane
from agent_batch.core import eligibility, merge, naming, prompts, results, risk, rounds
from agent_batch.core.config import BLOCKED, HIGH_RISK
from agent_batch.core.merge import MergeStatus
from agent_batch.core.model import (
    ClaudeRun,
    Finding,
    FoundIssue,
    ImplementResult,
    Issue,
    IssueReport,
    Outcome,
    ReviewResult,
    Risk,
    RunDenial,
    RunKind,
)
from agent_batch.shell.proc import CommandError

RISK_PATHS = ".claude/risk-paths"
# GitHub's reason for an issue that its PR closed; "NOT_PLANNED" means the work was dropped.
CLOSED_AS_COMPLETED = "COMPLETED"


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
    _announce(ctx, report)
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
    ctx.git.start_branch(lane.worktree, job.branch)
    ctx.events.emit("issue_started", lane=lane.index, issue=number, branch=job.branch)
    _start_work(ctx, lane, job)
    review_until_approved(ctx, lane, job)
    publish(ctx, lane, job)
    return _route(ctx, lane, job)


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


def _start_work(ctx: Context, lane: Lane, job: Job) -> None:
    reuse = lane.session_id is not None and lane.session_issues < ctx.config.issues_per_session
    prompt = prompts.implement(job.issue.number)
    run = ctx.claude.implement(lane.worktree, prompt, lane.session_id if reuse else None)
    lane.session_issues = lane.session_issues + 1 if reuse else 1
    lane.session_id = run.session_id
    _accept_work(ctx, lane, job, run)


def _accept_work(ctx: Context, lane: Lane, job: Job, run: ClaudeRun) -> None:
    work = results.to_implement(_checked(ctx, run, job.report, "implementation"))
    if work is None:
        raise Stopped(Outcome.FAILED, "the implementer's answer doesn't match its schema")
    if work.status == "blocked":
        raise Stopped(Outcome.BLOCKED, work.message)
    if work.status == "failed":
        raise Stopped(Outcome.FAILED, work.message)
    require_committed(ctx, lane)
    job.work = work


def _checked(ctx: Context, run: ClaudeRun, report: IssueReport, what: RunKind) -> dict[str, object]:
    for denial in run.denials:
        report.denials.append(RunDenial(what, denial))
        ctx.events.emit(
            "permission_denied",
            issue=report.number,
            run=what,
            tool=denial.tool,
            input=denial.tool_input,
        )
    report.cost_usd += run.cost_usd
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


def review_until_approved(ctx: Context, lane: Lane, job: Job) -> None:
    """Reviews, sends findings back to the implementer, and gives up after the last round."""
    most = ctx.config.review_rounds
    for attempt in range(1, most + 1):
        job.report.review_rounds = attempt
        review = review_once(ctx, lane, job)
        if review.approved:
            job.findings = review.findings
            return
        if attempt == most:
            findings = prompts.findings_list(review.findings)
            raise Stopped(
                Outcome.BLOCKED,
                f"The review still asks for changes after {most} rounds:\n\n{findings}",
            )
        prompt = prompts.fix(job.issue.number, review.findings)
        run = ctx.claude.implement(lane.worktree, prompt, lane.session_id)
        lane.session_id = run.session_id or lane.session_id
        _accept_work(ctx, lane, job, run)


def review_once(ctx: Context, lane: Lane, job: Job) -> ReviewResult:
    """One review of the branch, which gets what its earlier reviews found (SPEC §5)."""
    earlier = rounds.earlier(ctx.events.project_records("reviewed"), job.branch)
    number = len(earlier) + 1
    head = ctx.git.head(lane.worktree)
    started = ctx.clock()
    run = ctx.claude.review(lane.worktree, prompts.review(job.issue.number, earlier))
    seconds = ctx.clock() - started
    answer = results.to_review(_checked(ctx, run, job.report, "review"))
    if answer is None:
        raise Stopped(Outcome.FAILED, "the reviewer's answer doesn't match its schema")
    review, filed = rounds.settle(answer, number)
    # The issues go before the event: if filing fails, this round isn't logged and runs again.
    # That can file an issue twice, but the next round never reads as filed a finding that wasn't.
    for finding in filed:
        _file(ctx, job, rounds.found_issue(finding, number))
    # Every finding, filed ones included, so that the next review can read what this one found.
    # Its cost and time too: `ship`'s reviews count in no summary, only in the acceptance's numbers.
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
        seconds=round(seconds, 1),
    )
    return review


def publish(ctx: Context, lane: Lane, job: Job) -> int:
    """Pushes the branch, opens or updates its PR and files the work found along the way."""
    work = _work(job)
    ctx.git.push(lane.worktree, job.branch)
    title, body = _pr_text(job)
    pr = ctx.gh.find_pr(job.branch)
    if pr is None:
        pr = ctx.gh.create_pr(job.branch, ctx.config.base_branch, title, body)
        ctx.events.emit("pr_opened", lane=lane.index, issue=job.issue.number, pr=pr)
    else:
        ctx.gh.edit_pr(pr, title, body)
        ctx.events.emit("pr_updated", lane=lane.index, issue=job.issue.number, pr=pr)
    job.report.pr = pr
    for found in work.found:
        _file(ctx, job, found)
    return pr


def _file(ctx: Context, job: Job, found: FoundIssue) -> None:
    """Files work found along the way as an issue of its own (SPEC §4.5)."""
    body = f"{found.body.rstrip()}\n\nFound while working on #{job.issue.number}."
    number = ctx.gh.create_issue(found.title, body, found.kind)
    ctx.events.emit("issue_found", issue=job.issue.number, found=number)


def _work(job: Job) -> ImplementResult:
    if job.work is None:
        raise Stopped(Outcome.FAILED, "there's no implementation to publish")
    return job.work


def _pr_text(job: Job) -> tuple[str, str]:
    """The PR's title and body: the implementer's, with the approved review's findings."""
    work = _work(job)
    title = naming.pr_title(work.title, job.issue)
    return title, naming.pr_body(work.pr_body, job.issue.number, job.findings)


def classify(ctx: Context, lane: Lane, job: Job) -> Risk:
    # The project's risk paths come from the base branch, where no agent of this batch wrote.
    patterns = risk.parse_patterns(ctx.git.base_file(lane.worktree, RISK_PATHS) or "")
    return risk.classify(ctx.git.changed_files(lane.worktree), patterns, job.issue)


def hold(ctx: Context, pr: int, level: Risk) -> None:
    """Leaves a high-risk PR for the owner to merge, saying why."""
    ctx.gh.pr_add_label(pr, HIGH_RISK)
    reasons = "\n".join(f"- {reason}" for reason in level.reasons)
    ctx.gh.pr_comment(pr, f"**High risk: the owner merges this PR.**\n\n{reasons}\n")


def _route(ctx: Context, lane: Lane, job: Job) -> Outcome:
    level = classify(ctx, lane, job)
    if level.high:
        hold(ctx, _pr(job), level)
        ctx.events.emit("waiting_owner", lane=lane.index, issue=job.issue.number, pr=_pr(job))
        return Outcome.WAITING_OWNER
    return _merge(ctx, lane, job, resolve_conflicts=True)


def _pr(job: Job) -> int:
    if job.report.pr is None:
        raise Stopped(Outcome.FAILED, "the issue has no PR")
    return job.report.pr


def _merge(ctx: Context, lane: Lane, job: Job, *, resolve_conflicts: bool) -> Outcome:
    pr = _pr(job)
    ctx.gh.arm_merge(pr, ctx.git.head(lane.worktree))
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
        status = merge.decide(ctx.gh.pr_state(pr))
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
        run = ctx.claude.resolve(lane.worktree, prompt)
        answer = results.to_resolve(_checked(ctx, run, job.report, "conflict resolution"))
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
    ctx.git.push(lane.worktree, job.branch)
    title, body = _pr_text(job)
    ctx.gh.edit_pr(_pr(job), title, body)


def _announce(ctx: Context, report: IssueReport) -> None:
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
        ctx.gh.add_label(report.number, BLOCKED)
        ctx.gh.comment(report.number, body)
    except CommandError as error:
        report.unannounced = True
        ctx.events.emit("announce_failed", issue=report.number, detail=str(error))
