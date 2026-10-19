"""While a run streams, its lane shows a cost estimate for its tokens so far (#144)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_batch.core import progress
from agent_batch.core.progress import LaneState, Row
from agent_batch.shell.status import StatusBoard
from conftest import World

BATCH = 1
NOW = 1_000.0


def board_lanes(path: Path) -> dict[int, LaneState]:
    record = progress.parse_status(path.read_text(encoding="utf-8"))
    assert record is not None
    return dict(record[1])


def cost_cell(state: LaneState) -> str:
    table = progress.render([Row("batch-1", 1, state)], NOW)
    return table.splitlines()[1].split("  ")[-1].strip()


def status_row(world: World, capsys: pytest.CaptureFixture[str], issue: int) -> str:
    capsys.readouterr()
    assert world.run("status") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if f"#{issue}" in line]
    assert len(rows) == 1, rows
    return rows[0]


def read(tokens: int, message: str | None = None) -> dict[str, object]:
    tool: dict[str, object] = {"name": "Read", "input": {"file_path": "README.md"}}
    tool["tokens"] = tokens
    if message is not None:
        tool["message"] = message
    return tool


def test_a_streaming_runs_tokens_are_priced_at_the_batchs_average_cost_per_token(
    tmp_path: Path,
) -> None:
    path = tmp_path / "batch-1" / "status.json"
    board = StatusBoard(path, 101)
    board.start(1, LaneState(10, progress.IMPLEMENTATION, 0.0, 2))
    board.used(1, 600)
    board.used(1, 400)
    board.spent(1, 0.10)
    board.start(2, LaneState(11, progress.IMPLEMENTATION, 0.0, 2))

    board.used(2, 300)
    board.used(2, 200)

    lanes = board_lanes(path)
    assert lanes[2].tokens == 500
    assert lanes[2].estimate_usd == pytest.approx(0.05)
    assert lanes[1].cost_usd == pytest.approx(0.10)
    assert lanes[1].tokens == 0
    assert lanes[1].estimate_usd is None


def test_a_runs_message_counts_its_tokens_once_however_many_blocks_repeat_it(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    world.script("implement", 10, {"tools": [read(1000)], "cost": 0.10})
    tools = [read(300, "msg_a"), read(300, "msg_a"), read(200, "msg_b")]
    world.script("implement", 11, {"tools": tools, "snapshot": True})

    assert world.run("run", str(BATCH)) == 0

    world.restore_status(world.status_snapshots()[-1])
    found = status_row(world, capsys, 11)
    assert "~$0.05" in found
    assert "estimate" in found


def test_before_any_run_has_finished_the_status_shows_the_runs_tokens_and_no_estimate(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {"tools": [read(1000)], "snapshot": True})

    assert world.run("run", str(BATCH)) == 0

    [snapshot] = world.status_snapshots()
    world.restore_status(snapshot)
    found = status_row(world, capsys, 10)
    assert "1,000 tokens" in found
    assert "~$" not in found
    assert "estimate" not in found


def test_the_cost_column_shows_the_tokens_alone_until_a_run_has_finished() -> None:
    state = LaneState(10, progress.IMPLEMENTATION, NOW, 2, tokens=1000)

    assert cost_cell(state) == "$0.00 + 1,000 tokens"


def test_status_marks_an_estimated_cost_as_an_estimate_next_to_the_measured_one() -> None:
    state = LaneState(10, progress.REVIEW, NOW, 2, cost_usd=0.10, tokens=500, estimate_usd=0.05)

    assert cost_cell(state) == "$0.10 + ~$0.05 (estimate)"


def test_a_lane_with_no_run_streaming_shows_only_its_measured_cost() -> None:
    state = LaneState(10, progress.REVIEW, NOW, 2, cost_usd=0.10)

    assert cost_cell(state) == "$0.10"


def test_the_batchs_summary_reports_only_the_measured_cost(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    world.script("implement", 10, {"tools": [read(1000)], "cost": 0.10})
    world.script("implement", 11, {"tools": [read(5000)], "cost": 0.02})

    assert world.run("run", str(BATCH)) == 0

    summary: str = world.gh()["issues"][str(BATCH)]["comments"][-1]
    # Each issue's implementation and its review, at 0.01 by default: no estimate in it.
    expected = 0.10 + 0.01 + 0.02 + 0.01
    assert f"**Notional cost:** ${expected:.2f}" in summary.splitlines()
    assert "estimate" not in summary.lower()


def test_status_json_keeps_the_runs_tokens_and_its_estimate(tmp_path: Path) -> None:
    path = tmp_path / "ship-10" / "status.json"
    board = StatusBoard(path, 101)
    board.start(0, LaneState(10, progress.REVIEW, 0.0, 1))

    board.used(0, 250)

    lane = json.loads(path.read_text())["lanes"]["0"]
    assert lane["tokens"] == 250
    assert lane["estimate_usd"] is None
