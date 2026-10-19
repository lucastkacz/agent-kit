"""The edges of a lane's live state: short actions, status files and their table (small tests)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent_batch.core import progress
from agent_batch.core.progress import LaneState, Row
from agent_batch.shell import proc
from agent_batch.shell.proc import CommandError

ROOT = "/work/lane-1"


def assistant(*blocks: object) -> str:
    return json.dumps({"type": "assistant", "message": {"content": list(blocks)}})


@pytest.mark.parametrize(
    "line",
    [
        "not json",
        json.dumps(["a list"]),
        json.dumps({"type": "user", "message": {"content": []}}),
        json.dumps({"type": "assistant", "message": "text"}),
        json.dumps({"type": "assistant", "message": {"content": "text"}}),
        assistant({"type": "text", "text": "Done."}, "not a block"),
    ],
)
def test_a_line_without_a_tool_use_has_no_action(line: str) -> None:
    assert progress.actions(line, ROOT) == []


def test_each_tool_use_of_a_message_is_an_action() -> None:
    line = assistant(
        {"type": "tool_use", "name": "Read", "input": {"file_path": f"{ROOT}/a.py"}},
        {"type": "tool_use", "name": "Grep", "input": {"pattern": "SECRET"}},
    )

    assert progress.actions(line, ROOT) == ["Read(a.py)", "Grep"]


@pytest.mark.parametrize(
    ("tool", "tool_input", "shown"),
    [
        ("Read", {"file_path": "/elsewhere/b.py"}, "Read(/elsewhere/b.py)"),
        ("Write", {"content": "no path"}, "Write"),
        ("Bash", {"command": "  \n"}, "Bash"),
        ("Bash", {"command": "\nmake check\nmore"}, "Bash(make check)"),
        ("Bash", "not an object", "Bash"),
        ("Glob", {"pattern": "**/*.py"}, "Glob"),
    ],
)
def test_the_short_form_of_a_tool_use(tool: str, tool_input: object, shown: str) -> None:
    assert progress.short_action(tool, tool_input, ROOT) == shown


def test_a_long_input_is_cut_to_a_fixed_length() -> None:
    shown = progress.short_action("Bash", {"command": "x" * 200}, ROOT)

    assert shown == f"Bash({'x' * (progress.INPUT_LENGTH - 1)}…)"


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "[]",
        json.dumps({"pid": "1", "lanes": {}}),
        json.dumps({"pid": 1, "lanes": []}),
    ],
)
def test_a_status_file_that_cant_be_read_is_left_out(text: str) -> None:
    assert progress.parse_status(text) is None


def test_a_lane_that_cant_be_read_is_left_out_of_its_status_file() -> None:
    good = {"issue": 1, "step": "review", "started": 0, "rounds": 2, "round": 1, "action": ""}
    lanes = {
        "1": {**good, "cost_usd": 0.5},
        "2": "not a lane",
        "3": {**good, "issue": True, "cost_usd": 0},
        "4": {**good, "step": 3, "cost_usd": 0},
        "5": {**good, "cost_usd": None},
        "lane": {**good, "cost_usd": 0},
    }

    parsed = progress.parse_status(json.dumps({"pid": 7, "lanes": lanes}))

    assert parsed == (7, [(1, LaneState(1, "review", 0.0, 2, 1, "", None, 0.5))])


def test_a_step_outside_the_pipeline_shows_by_its_name() -> None:
    state = LaneState(3, "cleanup", 0.0, 2)

    table = progress.render([Row("batch-1", 1, state)], 59.0)

    cells = re.split(r"\s{2,}", table.splitlines()[1])
    assert cells == ["batch-1, lane 1", "#3", "cleanup", "-", "-", "0 min", "$0.00"]


def test_the_command_must_exist_to_stream() -> None:
    with pytest.raises(CommandError, match="isn't installed"):
        proc.stream(["no-such-command-107"], Path.cwd(), {}, 5, print)
