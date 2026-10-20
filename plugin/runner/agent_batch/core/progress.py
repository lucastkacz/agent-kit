"""What each lane is doing right now, which `agent-batch status` shows (#107)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
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
# A message's tokens, each kind at the same weight: the rate comes from tokens counted this way.
TOKEN_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)
HEADER = ("RUN", "ISSUE", "STEP", "ROUND", "LAST ACTION", "TIME", "COST")
# A runner's row while it runs with no lane at work.
IDLE = "no lane at work"
NOTHING = "Nothing is running: no batch lane and no `agent-batch ship`.\n"
# The steps' names in the status line, which has little room (#108).
SHORT_STEPS = {
    IMPLEMENTATION: "implement",
    REVIEW: "review",
    PULL_REQUEST: "PR",
    RISK_AND_MERGE: "merge",
}
SEPARATOR = " · "


@dataclass(frozen=True)
class LaneState:
    """A lane's issue, its step, its review round out of `rounds`, and its runs' last tool use.

    `cost_usd` is what its ended runs cost; `tokens` are the running run's so far, and
    `estimate_usd` their price at the batch's rate, None until one of its runs has ended (#144).
    """

    issue: int
    step: str
    started: float
    rounds: int
    round: int = 0
    action: str = ""
    action_time: float | None = None
    cost_usd: float = 0.0
    tokens: int = 0
    estimate_usd: float | None = None


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


def session_cwd(text: str) -> str | None:
    """The working directory in the JSON that Claude Code passes a status line; None if absent."""
    try:
        session = json.loads(text)
    except json.JSONDecodeError:
        return None
    cwd = session.get("cwd") if isinstance(session, dict) else None
    return cwd if isinstance(cwd, str) and cwd else None


def usage(line: str) -> tuple[str, int] | None:
    """An assistant message's id and its tokens, in one line of the stream; None if it has none.

    The stream repeats a message once per block of its content, with the same id and usage.
    """
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(message, dict) or message.get("type") != "assistant":
        return None
    body = message.get("message")
    if not isinstance(body, dict):
        return None
    identity, counts = body.get("id"), body.get("usage")
    if not isinstance(identity, str) or not isinstance(counts, dict):
        return None
    numbers = [_whole(counts.get(field)) for field in TOKEN_FIELDS]
    return identity, sum(number for number in numbers if number is not None)


def stream_tokens(stdout: str) -> int:
    """A run's tokens, from all its stream printed: each message counts once, as `usage` reads."""
    counted: dict[str, int] = {}
    for text in stdout.splitlines():
        message = usage(text)
        if message is not None:
            counted.setdefault(*message)
    return sum(counted.values())


def earlier_rate(records: Sequence[Mapping[str, object]]) -> tuple[float, int]:
    """What the logged runs cost, and their tokens: the rate a resumed batch starts with (#156).

    A run logged without tokens, as before #156, or without a cost leaves it out: either would
    skew it, as in `StatusBoard.spent`.
    """
    spent_usd, spent_tokens = 0.0, 0
    for record in records:
        cost, tokens = _number(record.get("cost_usd")), _whole(record.get("tokens"))
        if cost is not None and cost > 0 and tokens is not None and tokens > 0:
            spent_usd += cost
            spent_tokens += tokens
    return spent_usd, spent_tokens


def estimate(tokens: int, spent_usd: float, spent_tokens: int) -> float | None:
    """The price of `tokens` at what the ended runs' tokens cost; None before any has ended."""
    if spent_tokens <= 0:
        return None
    return tokens * spent_usd / spent_tokens


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
    # The table goes to the owner's terminal.
    detail = _printable(detail)
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


def opened_by_runner(text: str) -> bool:
    """Whether a batch's runner opened this `status.json`, which then shows with no lanes (#217)."""
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(record, dict) and record.get("runner") is True


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
    tokens = _whole(raw.get("tokens")) or 0
    priced = _number(raw.get("estimate_usd"))
    return LaneState(
        issue, step, started, rounds, review_round, action, action_time, cost, tokens, priced
    )


def _whole(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def render(rows: Sequence[Row], now: float, idle: Sequence[str] = ()) -> str:
    """A table with a row per lane: its issue, step, round, last action, minutes and cost.

    And a row for each run in `idle`, whose runner runs with no lane at work, as before its
    first lane starts an issue (#217).
    """
    if not rows and not idle:
        return NOTHING
    keyed = [((row.run, row.lane), _cells(row, now)) for row in rows]
    keyed += [((run, -1), _runner_cells(run)) for run in idle]
    table = [HEADER, *(cells for _, cells in sorted(keyed))]
    widths = [max(len(line[column]) for line in table) for column in range(len(HEADER))]
    return "".join(
        "  ".join(cell.ljust(width) for cell, width in zip(line, widths, strict=True)).rstrip()
        + "\n"
        for line in table
    )


def line(rows: Sequence[Row], now: float, branch: str) -> str:
    """One short line: each lane's issue, step, and its round or its minutes (#108).

    With nothing running, the branch, so that the line still says where the session is.
    """
    if not rows:
        text = f"nothing running{SEPARATOR}{branch}" if branch else "nothing running"
    else:
        ordered = sorted(rows, key=lambda row: (row.run, row.lane))
        text = SEPARATOR.join(_short(row, now) for row in ordered)
    return _printable(text) + "\n"


def _short(row: Row, now: float) -> str:
    state = row.state
    name = f"L{row.lane}" if row.lane else "ship"
    step = SHORT_STEPS.get(state.step, state.step)
    if state.round:
        done = f"{state.round}/{max(state.round, state.rounds)}"
    else:
        done = f"{_whole_minutes(now - state.started)}m"
    return f"{name} #{state.issue} {step} {done}"


def _printable(text: str) -> str:
    # The terminal draws it: an escape sequence in a branch's name could rewrite or garble it.
    return "".join(char if char.isprintable() else "?" for char in text)


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
    return (run, f"#{state.issue}", step, review_round, action, minutes, _cost(state))


def _runner_cells(run: str) -> tuple[str, ...]:
    return (f"{run}, runner", "-", IDLE, "-", "-", "-", "-")


def _cost(state: LaneState) -> str:
    """The measured cost, then the running run's estimate, or its tokens before there's a rate."""
    measured = f"${state.cost_usd:.2f}"
    if not state.tokens:
        return measured
    if state.estimate_usd is None:
        return f"{measured} + {state.tokens:,} tokens"
    return f"{measured} + ~${state.estimate_usd:.2f} (estimate)"


def _ago(seconds: float) -> str:
    # Under a minute, the seconds say more than "0 min ago".
    if seconds < MINUTE:
        return f"{max(0, int(seconds))} s ago"
    return f"{_whole_minutes(seconds)} min ago"


def _whole_minutes(seconds: float) -> int:
    return max(0, int(seconds // MINUTE))
