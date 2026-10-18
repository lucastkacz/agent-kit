"""A batch: its lanes in parallel, within its budget, ending in a summary (SPEC §3.2)."""

from __future__ import annotations

import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from agent_batch.context import Context
from agent_batch.core import budget, plan, report
from agent_batch.core.config import BATCH
from agent_batch.core.model import Issue
from agent_batch.core.plan import BatchPlan, PlanError
from agent_batch.lane import Gate, run_lane


@dataclass(frozen=True)
class Limits:
    """The budget given on the command line, which wins over the batch issue's."""

    issues: int | None = None
    hours: float | None = None


def run_batch(ctx: Context, number: int, limits: Limits) -> int:
    batch = ctx.gh.issue(number)
    _check(batch, ctx.owner)
    lanes = plan.parse_plan(batch.body)
    gate = Gate(budget.resolve(limits.issues, limits.hours, lanes))
    ctx.events.emit("batch_started", batch=number, lanes=[list(lane) for lane in lanes.lanes])
    ctx.gh.comment(number, _started(ctx, lanes))
    started = time.monotonic()
    workers = max(1, min(ctx.config.lanes, len(lanes.lanes)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(run_lane, ctx, gate, index, issues)
            for index, issues in enumerate(lanes.lanes, start=1)
        ]
        reports = [issue_report for future in futures for issue_report in future.result()]
    ctx.gh.comment(number, report.render(reports, time.monotonic() - started))
    outcomes = Counter(issue_report.outcome.value for issue_report in reports)
    ctx.events.emit("batch_finished", batch=number, outcomes=dict(outcomes))
    return 0


def _check(batch: Issue, owner: str) -> None:
    if BATCH not in batch.labels:
        raise PlanError(f"#{batch.number} isn't a batch: it isn't labeled {BATCH}")
    if batch.author != owner:
        raise PlanError(f"#{batch.number} wasn't opened by the owner")
    if batch.state != "OPEN":
        raise PlanError(f"#{batch.number} is closed")


def _started(ctx: Context, lanes: BatchPlan) -> str:
    return (
        "**The batch started.**\n\n"
        f"{plan.format_lanes(lanes.lanes)}\n\n"
        f"Up to {ctx.config.lanes} lanes run at a time. The summary follows here when it ends.\n"
    )
