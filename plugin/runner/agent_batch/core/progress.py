"""What each lane is doing right now, which `agent-batch status` shows (#107)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePath

IMPLEMENTATION = "implementation"
REVIEW = "review"
PULL_REQUEST = "pull request"
RISK_AND_MERGE = "risk and merge"
# The steps of the pipeline that the runner goes through (SPEC §5).
STEPS = (IMPLEMENTATION, REVIEW, PULL_REQUEST, RISK_AND_MERGE)
# The last action's input is cut to this many characters: a path, or the start of a command.
INPUT_LENGTH = 50
PATH_TOOLS = frozenset({"Read", "Edit", "Write"})
MINUTE = 60
HEADER = ("RUN", "ISSUE", "STEP", "ROUND", "LAST ACTION", "TIME", "COST")
NOTHING = "Nothing is running: no batch lane and no `agent-batch ship`.\n"


@dataclass(frozen=True)
class LaneState:
    """A lane's issue, its step, its review round out of `rounds`, and its runs' last tool use."""

    issue: int
    step: str
    started: float
    rounds: int
    round: int = 0
    action: str = ""
    action_time: float | None = None
    cost_usd: float = 0.0


@dataclass(frozen=True)
class Row:
    """A lane of a batch, or the lane 0 of an `agent-batch ship`, named by its state's folder."""

    run: str
    lane: int
    state: LaneState


def actions(line: str, root: str) -> list[str]:
    """The tool uses in one line of `claude -p --output-format stream-json`, in short form."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return []
    if not isinstance(message, dict) or message.get("type") != "assistant":
        return []
    body = message.get("message")
    content = body.get("content") if isinstance(body, dict) else None
    if not isinstance(content, list):
        return []
    return [
        short_action(str(block.get("name")), block.get("input"), root)
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]


def short_action(tool: str, tool_input: object, root: str) -> str:
    """The tool, and its file's path or its command's first line; never a file's content.

    A command's other lines can hold a heredoc's text, so they're left out too.
    """
    fields = tool_input if isinstance(tool_input, dict) else {}
    detail = ""
    if tool in PATH_TOOLS:
        detail = _relative(fields.get("file_path"), root)
    elif tool == "Bash":
        command = fields.get("command")
        lines = command.strip().splitlines() if isinstance(command, str) else []
        detail = lines[0] if lines else ""
    if not detail:
        return tool
    if len(detail) > INPUT_LENGTH:
        detail = detail[: INPUT_LENGTH - 1] + "…"
    return f"{tool}({detail})"


def _relative(path: object, root: str) -> str:
    if not isinstance(path, str):
        return ""
    try:
        return str(PurePath(path).relative_to(root))
    except ValueError:
        return path


def parse_status(text: str) -> tuple[int, list[tuple[int, LaneState]]] | None:
    """The runner's process id and its lanes, as `status.json` keeps them; None if unreadable."""
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        return None
    pid = record.get("pid") if isinstance(record, dict) else None
    lanes = record.get("lanes") if isinstance(record, dict) else None
    if not isinstance(pid, int) or not isinstance(lanes, dict):
        return None
    states = [(key, _state(raw)) for key, raw in lanes.items()]
    return pid, [(int(key), state) for key, state in states if key.isdigit() and state is not None]


def _state(raw: object) -> LaneState | None:
    if not isinstance(raw, dict):
        return None
    issue, rounds, review_round = (_whole(raw.get(key)) for key in ("issue", "rounds", "round"))
    started, cost = _number(raw.get("started")), _number(raw.get("cost_usd"))
    step, action = raw.get("step"), raw.get("action")
    if issue is None or rounds is None or review_round is None or started is None or cost is None:
        return None
    if not isinstance(step, str) or not isinstance(action, str):
        return None
    action_time = _number(raw.get("action_time"))
    return LaneState(issue, step, started, rounds, review_round, action, action_time, cost)


def _whole(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def render(rows: Sequence[Row], now: float) -> str:
    """A table with a row per lane: its issue, step, round, last action, minutes and cost."""
    if not rows:
        return NOTHING
    ordered = sorted(rows, key=lambda row: (row.run, row.lane))
    table = [HEADER, *(_cells(row, now) for row in ordered)]
    widths = [max(len(line[column]) for line in table) for column in range(len(HEADER))]
    return "".join(
        "  ".join(cell.ljust(width) for cell, width in zip(line, widths, strict=True)).rstrip()
        + "\n"
        for line in table
    )


def _cells(row: Row, now: float) -> tuple[str, ...]:
    state = row.state
    run = f"{row.run}, lane {row.lane}" if row.lane else row.run
    step = (
        f"{STEPS.index(state.step) + 1}/{len(STEPS)} {state.step}"
        if state.step in STEPS
        else state.step
    )
    # A conflict's re-review comes after the last round, as one more (SPEC §5): 3/3, not 3/2.
    review_round = f"{state.round}/{max(state.round, state.rounds)}" if state.round else "-"
    action = "-"
    if state.action and state.action_time is not None:
        action = f"{state.action}, {_ago(now - state.action_time)}"
    minutes = f"{_whole_minutes(now - state.started)} min"
    return (run, f"#{state.issue}", step, review_round, action, minutes, f"${state.cost_usd:.2f}")


def _ago(seconds: float) -> str:
    # Under a minute, the seconds say more than "0 min ago".
    if seconds < MINUTE:
        return f"{max(0, int(seconds))} s ago"
    return f"{_whole_minutes(seconds)} min ago"


def _whole_minutes(seconds: float) -> int:
    return max(0, int(seconds // MINUTE))
