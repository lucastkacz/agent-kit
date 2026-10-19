"""The pieces behind a resumed batch's rate and the status line's project check (#156, #171)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_batch.core import progress, project
from agent_batch.shell.events import EventLog
from agent_batch.shell.status import StatusBoard


def assistant(identity: str, tokens: int) -> str:
    usage = {"input_tokens": tokens, "output_tokens": 1}
    return json.dumps({"type": "assistant", "message": {"id": identity, "usage": usage}})


def test_a_streams_tokens_count_each_message_once() -> None:
    stdout = "\n".join(
        [
            '{"type": "system", "session_id": "s"}',
            assistant("msg_a", 99),
            assistant("msg_a", 99),
            "not json",
            assistant("msg_b", 9),
            '{"type": "result"}',
        ]
    )

    assert progress.stream_tokens(stdout) == 110


def test_the_earlier_rate_leaves_out_runs_logged_without_tokens_or_a_cost() -> None:
    records: list[dict[str, object]] = [
        {"cost_usd": 0.25, "tokens": 2000},
        {"cost_usd": 0.5},
        {"cost_usd": 0.0, "tokens": 300},
        {"cost_usd": 0.1, "tokens": True},
        {"cost_usd": "0.1", "tokens": 100},
        {"cost_usd": 0.75, "tokens": 3000},
    ]

    assert progress.earlier_rate(records) == (pytest.approx(1.0), 5000)


def test_with_no_earlier_run_there_is_no_rate() -> None:
    assert progress.earlier_rate([]) == (0.0, 0)


def test_a_seeded_board_prices_a_lanes_tokens_before_any_run_ends(tmp_path: Path) -> None:
    path = tmp_path / "batch-1" / "status.json"
    board = StatusBoard(path, 101, (0.2, 2000))
    board.start(1, progress.LaneState(10, progress.IMPLEMENTATION, 0.0, 2))

    board.used(1, 500)

    lane = json.loads(path.read_text())["lanes"]["1"]
    assert lane["estimate_usd"] == pytest.approx(0.05)


def test_a_logs_records_are_its_own_and_none_before_it_has_any(tmp_path: Path) -> None:
    mine = EventLog(tmp_path / "batch-2" / "events.jsonl")
    other = EventLog(tmp_path / "batch-1" / "events.jsonl")
    assert mine.records("reviewed") == []

    other.emit("reviewed", findings=[], cost_usd=1.0, tokens=10)
    mine.emit("reviewed", findings=[], cost_usd=0.5, tokens=5)
    mine.emit("issue_finished", issue=10)

    [record] = mine.records("reviewed")
    assert record["cost_usd"] == 0.5


@pytest.mark.parametrize(
    ("text", "enabled"),
    [
        ('{"enabledPlugins": {"agent-kit@agent-kit": true}}', True),
        ('{"enabledPlugins": {"agent-kit@elsewhere": true}}', True),
        ('{"enabledPlugins": {"agent-kit@agent-kit": "true"}}', False),
        ('{"enabledPlugins": {"other@agent-kit": true}}', False),
        ('{"enabledPlugins": ["agent-kit@agent-kit"]}', False),
        ("[]", False),
        ("", False),
    ],
)
def test_only_a_plugin_named_agent_kit_and_set_to_true_enables_it(text: str, enabled: bool) -> None:
    assert project.enables_agent_kit(text) is enabled
