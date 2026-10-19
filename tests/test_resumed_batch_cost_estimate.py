"""A resumed batch prices its running runs from the start, at its earlier runs' rate (#156)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from conftest import World

BATCH = 1
LIMIT_REACHED = {"error": "Claude usage limit reached."}


def read(tokens: int, message: str | None = None) -> dict[str, object]:
    tool: dict[str, object] = {
        "name": "Read",
        "input": {"file_path": "README.md"},
        "tokens": tokens,
    }
    if message is not None:
        tool["message"] = message
    return tool


def reviewed_events(world: World) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    return [record for record in records if record["event"] == "reviewed"]


def status_row(world: World, capsys: pytest.CaptureFixture[str], issue: int) -> str:
    capsys.readouterr()
    assert world.run("status") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if f"#{issue}" in line]
    assert len(rows) == 1, rows
    return rows[0]


def close_issue(world: World, number: int) -> None:
    """Closes the issue, as GitHub does when the PR that says `Closes #N` merges."""
    state = world.gh()
    state["issues"][str(number)]["state"] = "CLOSED"
    world.gh_state.write_text(json.dumps(state))


def test_the_event_log_keeps_each_reviews_tokens_beside_its_cost(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    tools = [read(1500, "msg_a"), read(1500, "msg_a"), read(500, "msg_b")]
    world.script("review", 10, {"tools": tools, "cost": 0.25})

    assert world.run("run", str(BATCH)) == 0

    [review] = reviewed_events(world)
    assert review["cost_usd"] == pytest.approx(0.25)
    assert review["tokens"] == 2000


def test_a_resumed_batch_prices_its_first_running_run_at_the_earlier_runs_rate(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    world.script("review", 10, {"tools": [read(2000)], "cost": 0.20})
    # The first run stops at #11; the second one starts #11 again, with no run of its own ended.
    world.script("implement", 11, LIMIT_REACHED, {"tools": [read(500)], "snapshot": True})
    world.run("run", str(BATCH))
    close_issue(world, 10)

    assert world.run("run", str(BATCH)) == 0

    [snapshot] = world.status_snapshots()
    world.restore_status(snapshot)
    found = status_row(world, capsys, 11)
    assert "~$0.05 (estimate)" in found
    assert "tokens" not in found
