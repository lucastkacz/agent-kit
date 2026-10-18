"""A batch: its lanes in parallel, within its budget, ending in a summary (SPEC §3.2)."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from agent_batch.context import Context
from agent_batch.core import budget, plan, report
from agent_batch.core.config import BATCH
from agent_batch.core.model import Issue
from agent_batch.core.plan import BatchPlan, PlanError
from agent_batch.lane import Gate, run_lane

ON_BATTERY = (
    "The Mac is on battery power, so it may sleep during the batch unless it's plugged in "
    "with its lid open."
)


@dataclass(frozen=True)
class Limits:
    """What the command line sets, which wins over the batch issue."""

    issues: int | None = None
    hours: float | None = None
    lanes: int | None = None


def run_batch(ctx: Context, number: int, limits: Limits, *, on_battery: bool) -> int:
    batch = ctx.gh.issue(number)
    _check(batch, ctx.owner)
    batch_plan = plan.parse_plan(batch.body)
    gate = Gate(budget.resolve(limits.issues, limits.hours, batch_plan), ctx.clock)
    at_once = plan.concurrency(limits.lanes, batch_plan, ctx.config.lanes)
    lanes = batch_plan.lanes
    ctx.events.emit("batch_started", batch=number, lanes=[list(lane) for lane in lanes])
    if on_battery:
        ctx.events.emit("on_battery", warning=ON_BATTERY)
    ctx.gh.comment(number, _started(batch_plan, at_once))
    started = ctx.clock()
    with ThreadPoolExecutor(max_workers=min(at_once, len(lanes))) as pool:
        futures = [
            pool.submit(run_lane, ctx, gate, index, issues)
            for index, issues in enumerate(lanes, start=1)
        ]
        reports = [issue_report for future in futures for issue_report in future.result()]
    ctx.gh.comment(number, report.render(reports, ctx.clock() - started))
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


def _started(batch_plan: BatchPlan, at_once: int) -> str:
    return (
        "**The batch started.**\n\n"
        f"{plan.format_lanes(batch_plan.lanes)}\n\n"
        f"**Lanes at a time:** {at_once}\n\n"
        "The summary follows here when it ends.\n"
    )
