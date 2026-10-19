"""Writing the live state never gets in the way of a run (#107)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from agent_batch.core.progress import LaneState
from agent_batch.shell.status import StatusBoard

WRITES = 200


def test_two_runners_writing_the_same_status_file_dont_trip_on_each_other(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "ship-10" / "status.json"
    boards = [StatusBoard(path, pid) for pid in (101, 102)]
    for board in boards:
        board.start(0, LaneState(10, "review", 0.0, 1))

    def write(board: StatusBoard) -> None:
        for count in range(WRITES):
            board.act(0, f"Bash(step {count})", float(count))

    threads = [threading.Thread(target=write, args=(board,)) for board in boards]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert capsys.readouterr().err == ""
    assert json.loads(path.read_text())["pid"] in (101, 102)
    assert [file.name for file in path.parent.iterdir()] == ["status.json"]


def test_a_status_that_cant_be_written_is_said_once_and_the_run_goes_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "batch-1"
    blocker.write_text("a file where the folder would go\n")
    board = StatusBoard(blocker / "status.json", 101)

    board.start(1, LaneState(10, "implementation", 0.0, 2))
    board.act(1, "Read(a.py)", 1.0)
    board.spent(1, 0.5)

    err = capsys.readouterr().err
    assert err.count("couldn't write") == 1
    assert str(blocker / "status.json") in err
