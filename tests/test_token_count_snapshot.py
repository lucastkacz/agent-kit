"""The token-count test reads the status once the runner recorded the last message's tokens (#239).

The runner here writes each tool use and each message's tokens late, as on a loaded computer: a
snapshot that kept the first change it saw would keep the status from before the last message's.
"""

from __future__ import annotations

import itertools
import time

import pytest

from agent_batch.core import progress
from agent_batch.shell.status import StatusBoard
from conftest import World

BATCH = 1
LATE = 0.3


@pytest.fixture(autouse=True)
def late_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each tool use and each message's tokens reach the status file late, one after the other."""
    act, used = StatusBoard.act, StatusBoard.used

    def late_act(board: StatusBoard, lane: int, action: str, when: float) -> None:
        time.sleep(LATE)
        act(board, lane, action, when)

    def late_used(board: StatusBoard, lane: int, tokens: int) -> None:
        time.sleep(LATE)
        used(board, lane, tokens)

    monkeypatch.setattr(StatusBoard, "act", late_act)
    monkeypatch.setattr(StatusBoard, "used", late_used)


def read(path: str, tokens: int, message: str) -> dict[str, object]:
    return {"name": "Read", "input": {"file_path": path}, "tokens": tokens, "message": message}


def last_status_row(world: World, capsys: pytest.CaptureFixture[str]) -> str:
    """#11's row of `agent-batch status`, as the run's last snapshot found it."""
    world.restore_status(world.status_snapshots()[-1])
    capsys.readouterr()
    assert world.run("status") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if "#11" in line]
    assert len(rows) == 1, rows
    return rows[0]


def run_repeated_message(world: World) -> None:
    """#10 sets the rate at $0.0001 a token; #11 sends msg_a in two blocks, then msg_b."""
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    world.script("implement", 10, {"tools": [read("README.md", 1000, "msg_10")], "cost": 0.10})
    last = {**read("b.md", 200, "msg_b"), "shows": "Read(b.md)"}
    tools = [read("a.md", 300, "msg_a"), read("a.md", 300, "msg_a"), last]
    world.script("implement", 11, {"tools": tools, "snapshot": True})
    assert world.run("run", str(BATCH)) == 0


def test_the_last_snapshot_has_the_last_messages_tokens_however_late_the_runner_shows_it(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    run_repeated_message(world)

    found = last_status_row(world, capsys)
    assert "~$0.05" in found
    assert "estimate" in found


def test_the_last_snapshot_shows_a_message_counted_once_per_block(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    usage = progress.usage
    blocks = itertools.count()

    def per_block(line: str) -> tuple[str, int] | None:
        found = usage(line)
        return None if found is None else (f"{found[0]}-{next(blocks)}", found[1])

    monkeypatch.setattr(progress, "usage", per_block)

    run_repeated_message(world)

    assert "~$0.08" in last_status_row(world, capsys)
