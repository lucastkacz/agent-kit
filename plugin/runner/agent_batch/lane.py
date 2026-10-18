"""A lane: issues that touch the same files, run in order in one worktree (SPEC §11.1)."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence

from agent_batch.context import Context, Lane
from agent_batch.core import budget
from agent_batch.core.budget import Budget
from agent_batch.core.model import IssueReport, Outcome
from agent_batch.pipeline import run_issue
from agent_batch.shell.proc import CommandError


class Gate:
    """Decides, across lanes, whether another issue may start."""

    def __init__(self, limits: Budget, clock: Callable[[], float]) -> None:
        self._limits = limits
        self._clock = clock
        self._started = 0
        self._stopped = False
        self._since = clock()
        self._lock = threading.Lock()

    def try_start(self) -> bool:
        with self._lock:
            elapsed = self._clock() - self._since
            if self._stopped or not budget.allows(self._limits, self._started, elapsed):
                return False
            self._started += 1
            return True

    def stop(self) -> None:
        with self._lock:
            self._stopped = True


def run_lane(ctx: Context, gate: Gate, index: int, numbers: Sequence[int]) -> list[IssueReport]:
    worktree = ctx.repo / ctx.config.state_dir / "worktrees" / f"lane-{index}"
    try:
        ctx.git.add_lane_worktree(ctx.repo, worktree)
    except CommandError as error:
        return _set_aside(ctx, numbers, Outcome.FAILED, f"the lane's worktree failed: {error}")
    try:
        return _run_issues(ctx, gate, Lane(index=index, worktree=worktree), numbers)
    finally:
        try:
            ctx.git.remove_worktree(ctx.repo, worktree)
        except CommandError as error:
            ctx.events.emit("cleanup_failed", lane=index, detail=str(error))


def _run_issues(ctx: Context, gate: Gate, lane: Lane, numbers: Sequence[int]) -> list[IssueReport]:
    reports: list[IssueReport] = []
    for position, number in enumerate(numbers):
        # Each issue a run reaches takes a slot, one an earlier run merged too, so a resumed
        # batch stays near the issue budget it was planned with.
        if not gate.try_start():
            rest = numbers[position:]
            return reports + _set_aside(ctx, rest, Outcome.DEFERRED, "the batch stopped")
        report = run_issue(ctx, lane, number)
        reports.append(report)
        if report.outcome is Outcome.INTERRUPTED:
            gate.stop()
        if report.outcome is not Outcome.MERGED:
            # The rest of the lane builds on this issue's files, so it waits for the next batch.
            rest = numbers[position + 1 :]
            return reports + _set_aside(ctx, rest, Outcome.DEFERRED, f"#{number} didn't merge")
    return reports


def _set_aside(
    ctx: Context, numbers: Sequence[int], outcome: Outcome, detail: str
) -> list[IssueReport]:
    for number in numbers:
        ctx.events.emit("issue_set_aside", issue=number, outcome=outcome.value, detail=detail)
    return [IssueReport(number=number, outcome=outcome, detail=detail) for number in numbers]
