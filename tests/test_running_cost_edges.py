"""The edges of a running run's tokens and their estimate (#144, small tests)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_batch.core import progress
from agent_batch.core.progress import LaneState
from agent_batch.shell.status import StatusBoard
from recorded_stream import check_recorded_stream

RECORDED = Path(__file__).parent / "contract" / "recorded" / "claude-stream.json"


def lanes(path: Path) -> dict[int, LaneState]:
    record = progress.parse_status(path.read_text(encoding="utf-8"))
    assert record is not None
    return dict(record[1])


@pytest.mark.parametrize(
    "line",
    [
        "not json",
        json.dumps(["a list"]),
        json.dumps({"type": "user", "message": {"id": "m", "usage": {"input_tokens": 1}}}),
        json.dumps({"type": "assistant", "message": "text"}),
        json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 1}}}),
        json.dumps({"type": "assistant", "message": {"id": "m", "usage": "none"}}),
    ],
)
def test_a_line_without_a_messages_usage_has_no_tokens(line: str) -> None:
    assert progress.usage(line) is None


def test_a_messages_tokens_add_every_kind_and_skip_what_isnt_a_count() -> None:
    usage = {
        "input_tokens": 2,
        "cache_creation_input_tokens": 30,
        "cache_read_input_tokens": 400,
        "output_tokens": "five",
        "service_tier": "standard",
    }
    line = json.dumps({"type": "assistant", "message": {"id": "msg_1", "usage": usage}})

    assert progress.usage(line) == ("msg_1", 432)


def test_the_recorded_streams_messages_each_carry_their_id_and_tokens() -> None:
    check_recorded_stream(RECORDED)


def test_a_run_that_ended_without_a_cost_leaves_the_rate_unset(tmp_path: Path) -> None:
    path = tmp_path / "batch-1" / "status.json"
    board = StatusBoard(path, 101)
    board.start(1, LaneState(10, progress.IMPLEMENTATION, 0.0, 2))
    board.used(1, 1000)
    board.spent(1, 0.0)

    board.used(1, 100)

    state = lanes(path)[1]
    assert state.tokens == 100
    assert state.estimate_usd is None


def test_a_run_that_ends_prices_the_other_lanes_running_tokens(tmp_path: Path) -> None:
    path = tmp_path / "batch-1" / "status.json"
    board = StatusBoard(path, 101)
    board.start(1, LaneState(10, progress.IMPLEMENTATION, 0.0, 2))
    board.start(2, LaneState(11, progress.IMPLEMENTATION, 0.0, 2))
    board.used(2, 200)
    board.used(1, 1000)

    board.spent(1, 0.10)

    assert lanes(path)[2].estimate_usd == pytest.approx(0.02)


def test_a_cost_for_a_lane_that_isnt_running_changes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "batch-1" / "status.json"
    board = StatusBoard(path, 101)
    board.start(1, LaneState(10, progress.IMPLEMENTATION, 0.0, 2))

    board.spent(2, 0.10)
    board.used(2, 100)

    assert set(lanes(path)) == {1}


def test_a_status_file_from_before_the_tokens_reads_as_none_running() -> None:
    raw = {"issue": 10, "step": "review", "started": 0.0, "rounds": 2, "round": 1}
    raw |= {"action": "", "action_time": None, "cost_usd": 0.5}
    record = progress.parse_status(json.dumps({"pid": 1, "lanes": {"1": raw}}))

    assert record is not None
    [(_, state)] = record[1]
    assert state.tokens == 0
    assert state.estimate_usd is None
