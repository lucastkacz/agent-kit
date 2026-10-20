"""After a merge conflict, `agent-batch status` shows the extra review, then the merge (#107)."""

from __future__ import annotations

import re

import pytest

from batch_runs import BATCH, CHANGES
from conftest import World

READ_README = {"name": "Read", "input": {"file_path": "README.md"}}


def cells(world: World, capsys: pytest.CaptureFixture[str], snapshot: dict[str, str]) -> list[str]:
    """The lane's row of `agent-batch status`, as the snapshot found the status file."""
    world.restore_status(snapshot)
    capsys.readouterr()
    assert world.run("status") == 0
    [row] = [line for line in capsys.readouterr().out.splitlines() if "#10" in line]
    return re.split(r"\s{2,}", row)


def test_after_a_conflict_status_shows_its_review_as_one_more_round_then_the_merge(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {"files": ["shared.txt"]})
    # Changes, then approved on the last round; the conflict's re-review comes after it.
    world.script("review", 10, CHANGES, {}, {"tools": [READ_README], "snapshot": True})
    conflict = {"file": "shared.txt", "content": "another lane\n"}
    world.pr_views(
        "10-issue-10",
        {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": conflict},
        {"state": "OPEN", "mergeable": "MERGEABLE", "snapshot": True},
    )

    assert world.run("run", str(BATCH)) == 0

    re_review, second_merge = world.status_snapshots()
    assert cells(world, capsys, re_review)[2:4] == ["2/4 review", "3/3"]
    assert cells(world, capsys, second_merge)[2:4] == ["4/4 risk and merge", "3/3"]
    assert "merged 1" in world.gh()["issues"][str(BATCH)]["comments"][-1]
