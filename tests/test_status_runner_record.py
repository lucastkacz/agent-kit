"""Only a runner's own open record shows with no lanes, and a run's end takes it away (#217)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_batch.core.progress import LaneState
from agent_batch.shell.status import StatusBoard
from conftest import World
from ship_branches import branch_with_work

BATCH = 1


def status(world: World, capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    assert world.run("status") == 0
    return capsys.readouterr().out


def test_after_a_ship_ends_status_says_nothing_is_running(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "feat: add it", "--body-file", str(body)) == 0

    assert "Nothing is running" in status(world, capsys)


def test_a_record_left_with_no_lanes_by_an_older_runner_doesnt_show_as_a_runner(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = world.project / ".agent-batch" / f"batch-{BATCH}"
    folder.mkdir(parents=True)
    # Its process id runs, as a reused one does, or as any does where it can't be told.
    (folder / "status.json").write_text(json.dumps({"pid": os.getpid(), "lanes": {}}))

    assert "Nothing is running" in status(world, capsys)


def test_closing_a_board_leaves_another_runners_file_alone(tmp_path: Path) -> None:
    path = tmp_path / "batch-1" / "status.json"
    mine, theirs = StatusBoard(path, 101), StatusBoard(path, 102)
    mine.open()
    theirs.start(1, LaneState(10, "implementation", 0.0, 2))

    mine.close()

    assert json.loads(path.read_text())["pid"] == 102


def test_closing_a_board_removes_its_own_file(tmp_path: Path) -> None:
    path = tmp_path / "batch-1" / "status.json"
    board = StatusBoard(path, 101)
    board.open()

    board.close()

    assert not path.exists()
