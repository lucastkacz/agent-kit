"""A batch's budget (SPEC §11.2)."""

from __future__ import annotations

from dataclasses import dataclass

from agent_batch.core.plan import BatchPlan

SECONDS_PER_HOUR = 3600


@dataclass(frozen=True)
class Budget:
    max_issues: int | None = None
    max_seconds: float | None = None


def resolve(issues: int | None, hours: float | None, plan: BatchPlan) -> Budget:
    """The command line's limits, or else the ones in the batch issue."""
    max_issues = issues if issues is not None else plan.max_issues
    max_hours = hours if hours is not None else plan.max_hours
    return Budget(
        max_issues=max_issues,
        max_seconds=max_hours * SECONDS_PER_HOUR if max_hours is not None else None,
    )


def allows(budget: Budget, started: int, elapsed: float) -> bool:
    """Whether one more issue may start."""
    if budget.max_issues is not None and started >= budget.max_issues:
        return False
    return budget.max_seconds is None or elapsed < budget.max_seconds
