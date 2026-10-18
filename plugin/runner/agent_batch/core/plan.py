"""The lane plan, lanes at a time, budget and model written in a batch's tracking issue (§4.3)."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

LANE_LINE = re.compile(r"^[ \t]*lane[ \t]+\d+[ \t]*:(.*)$", re.IGNORECASE | re.MULTILINE)
ISSUE_REF = re.compile(r"#(\d+)\b")
BUDGET_LINE = re.compile(r"^[ \t]*budget[ \t]*:(.*)$", re.IGNORECASE | re.MULTILINE)
# The lookbehind keeps the count from matching the tail of a decimal, such as `0 issues` in `1.0`.
BUDGET_ISSUES = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*issues?\b", re.IGNORECASE)
BUDGET_HOURS = re.compile(r"(\d+(?:\.\d+)?)\s*h(?:ours?)?\b", re.IGNORECASE)
LANES_AT_ONCE_LINE = re.compile(r"^[ \t]*lanes[ \t]*:(.*)$", re.IGNORECASE | re.MULTILINE)
MODEL_LINE = re.compile(r"^[ \t]*model[ \t]*:(.*)$", re.IGNORECASE | re.MULTILINE)
MODEL_NAME = re.compile(r"^[^\s,]+$")
# The levels `claude --effort` takes.
EFFORTS = ("low", "medium", "high", "xhigh", "max")


class PlanError(ValueError):
    """The batch issue's plan can't be run."""


@dataclass(frozen=True)
class BatchPlan:
    lanes: tuple[tuple[int, ...], ...]
    max_issues: int | None = None
    max_hours: float | None = None
    lanes_at_once: int | None = None
    model: str | None = None
    effort: str | None = None


def parse_plan(body: str) -> BatchPlan:
    lanes = tuple(
        lane
        for match in LANE_LINE.finditer(body)
        if (lane := tuple(int(n) for n in ISSUE_REF.findall(match.group(1))))
    )
    if not lanes:
        raise PlanError("the batch issue has no lane plan, such as a line `Lane 1: #12, #15`")
    repeated = sorted(
        n for n, times in Counter(n for lane in lanes for n in lane).items() if times > 1
    )
    if repeated:
        listed = ", ".join(f"#{n}" for n in repeated)
        raise PlanError(f"these issues are in more than one lane: {listed}")
    max_issues, max_hours = _budget(body)
    model, effort = _model(body)
    return BatchPlan(lanes, max_issues, max_hours, _lanes_at_once(body), model, effort)


def _model(body: str) -> tuple[str | None, str | None]:
    """`Model: opus, max` is a model and an effort; `Model: sonnet`, a model alone."""
    line = MODEL_LINE.search(body)
    if line is None:
        return None, None
    text = line.group(1).strip()
    model, comma, effort = (part.strip() for part in text.partition(","))
    if not MODEL_NAME.match(model) or (comma and effort not in EFFORTS):
        raise PlanError(
            "`Model:` needs a model, such as `opus`, then optionally a comma and an effort "
            f"({', '.join(EFFORTS)}), not {text!r}"
        )
    return model, effort or None


def choose_model(
    model: str | None, effort: str | None, batch: BatchPlan
) -> tuple[str | None, str | None]:
    """The runs' model and effort: each from the command line, else from the batch issue."""
    return (model or batch.model, effort or batch.effort)


def describe_model(model: str | None, effort: str | None) -> list[str]:
    """The model and effort as the batch's comments state them, when they're set."""
    shown = (("Model", model), ("Effort", effort))
    return [f"**{name}:** {value}" for name, value in shown if value is not None]


def _lanes_at_once(body: str) -> int | None:
    line = LANES_AT_ONCE_LINE.search(body)
    if line is None:
        return None
    text = line.group(1).strip()
    if not text.isdigit() or int(text) < 1:
        raise PlanError(f"`Lanes:` needs a whole number of at least 1, not {text!r}")
    return int(text)


def concurrency(requested: int | None, batch: BatchPlan, default: int) -> int:
    """Lanes at a time: the command line's count, else the batch issue's, else the default."""
    if requested is not None:
        return requested
    if batch.lanes_at_once is not None:
        return batch.lanes_at_once
    return default


def _budget(body: str) -> tuple[int | None, float | None]:
    line = BUDGET_LINE.search(body)
    if line is None:
        return None, None
    issues = BUDGET_ISSUES.search(line.group(1))
    hours = BUDGET_HOURS.search(line.group(1))
    if issues and not issues.group(1).isdigit():
        raise PlanError(f"`Budget:` needs a whole number of issues, not {issues.group(0)!r}")
    if issues and int(issues.group(1)) == 0:
        raise PlanError(f"`Budget:` needs at least 1 issue, not {issues.group(0)!r}")
    if hours and float(hours.group(1)) == 0:
        raise PlanError(f"`Budget:` needs more than 0 hours, not {hours.group(0)!r}")
    return (
        int(issues.group(1)) if issues else None,
        float(hours.group(1)) if hours else None,
    )


def format_lanes(lanes: Sequence[Sequence[int]]) -> str:
    """The lane plan as planning writes it into the batch issue."""
    return "\n".join(
        f"Lane {index}: {', '.join(f'#{n}' for n in lane)}"
        for index, lane in enumerate(lanes, start=1)
    )
