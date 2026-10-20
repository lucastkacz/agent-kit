"""`agent-batch status`: each lane's issue, step, review round and last action, live (#107)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from batch_runs import BATCH
from conftest import World, git

LONG_LINE = "uv run pytest " + "tests/test_a_long_name.py " * 10
TOOLS = [
    {"name": "Read", "input": {"file_path": "src/app.py"}},
    {
        "name": "Edit",
        "input": {
            "file_path": "src/app.py",
            "old_string": "SECRET-OLD",
            "new_string": "SECRET-NEW",
        },
    },
    {"name": "Write", "input": {"file_path": "notes.md", "content": "SECRET-CONTENT"}},
    {
        "name": "Bash",
        "input": {"command": f"{LONG_LINE}\necho SECRET-SECOND-LINE", "description": "Tests"},
    },
]
SHOWN = [
    "Read(src/app.py)",
    "Edit(src/app.py)",
    "Write(notes.md)",
    "Bash(uv run pytest tests/test_a_long_name.py",
]
READ_README = {"name": "Read", "input": {"file_path": "README.md"}}


def status(world: World, capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    assert world.run("status") == 0
    return capsys.readouterr().out


def row(out: str, issue: int) -> str:
    rows = [line for line in out.splitlines() if f"#{issue}" in line]
    assert len(rows) == 1, out
    return rows[0]


def lane_state(
    issue: int, step: str, review_round: int, action: str, numbers: tuple[float, float, float]
) -> dict[str, object]:
    """A lane's state, with its last action `ago` seconds back, `minutes` in and its `cost`."""
    ago, minutes, cost = numbers
    now = time.time()
    return {
        "issue": issue,
        "step": step,
        "round": review_round,
        "rounds": 2,
        "action": action,
        "action_time": now - ago,
        "started": now - minutes * 60,
        "cost_usd": cost,
    }


def write_status(world: World, run: str, lanes: dict[str, object], pid: int) -> None:
    folder = world.project / ".agent-batch" / run
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "status.json").write_text(json.dumps({"pid": pid, "lanes": lanes}))


def branch_with_work(world: World, branch: str) -> Path:
    git(world.project, "switch", "--quiet", "--create", branch)
    (world.project / "feature.txt").write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: work")
    body = world.root / "body.md"
    body.write_text("Adds the feature.\n")
    return body


def test_each_tool_use_updates_its_lanes_last_action_with_the_tool_and_its_short_input(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {"tools": TOOLS, "snapshot": True})

    assert world.run("run", str(BATCH)) == 0

    snapshots = world.status_snapshots()
    assert len(snapshots) == len(TOOLS), "the runner didn't follow the run's tool uses"
    for snapshot, shown in zip(snapshots, SHOWN, strict=True):
        assert snapshot, "no status file while the run went on"
        assert "SECRET" not in json.dumps(snapshot)
        world.restore_status(snapshot)
        out = status(world, capsys)
        assert shown in row(out, 10)
        assert "SECRET" not in out
        assert LONG_LINE.strip() not in out


def test_status_prints_a_row_per_lane_of_the_running_batch_and_one_per_running_ship(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    write_status(
        world,
        f"batch-{BATCH}",
        {
            "1": lane_state(10, "review", 1, "Read(README.md)", (125, 25, 1.5)),
            "2": lane_state(11, "implementation", 0, "Bash(make test)", (200, 3, 0)),
        },
        os.getpid(),
    )
    write_status(
        world,
        "ship-12",
        {"0": lane_state(12, "pull request", 1, "Bash(git push)", (600, 12, 0.75))},
        os.getpid(),
    )

    out = status(world, capsys)

    assert len([line for line in out.splitlines() if "#" in line]) == 3, out
    first = row(out, 10)
    for shown in ("batch-1", "lane 1", "2/4 review", "1/2", "Read(README.md)", "2 min ago"):
        assert shown in first
    assert "25 min" in first
    assert "$1.50" in first
    second = row(out, 11)
    for shown in ("batch-1", "lane 2", "1/4 implementation", "Bash(make test)", "3 min ago"):
        assert shown in second
    assert "$0.00" in second
    shipped = row(out, 12)
    for shown in ("ship-12", "3/4 pull request", "1/2", "Bash(git push)", "10 min ago", "12 min"):
        assert shown in shipped
    assert "$0.75" in shipped


def test_during_a_batch_review_status_shows_its_step_round_action_and_cost_so_far(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, {"tools": [READ_README], "snapshot": True})

    assert world.run("run", str(BATCH)) == 0

    [snapshot] = world.status_snapshots()
    world.restore_status(snapshot)
    found = row(status(world, capsys), 10)
    for shown in ("batch-1", "lane 1", "2/4 review", "1/2", "Read(README.md)", "ago", "0 min"):
        assert shown in found
    assert "$0.01" in found


def test_during_a_ship_status_shows_its_row(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")
    world.script("review", 10, {"tools": [READ_README], "snapshot": True})

    assert world.run("ship", "10", "--title", "feat: add it", "--body-file", str(body)) == 0

    [snapshot] = world.status_snapshots()
    world.restore_status(snapshot)
    found = row(status(world, capsys), 10)
    for shown in ("ship-10", "2/4 review", "1/1", "Read(README.md)", "ago"):
        assert shown in found


def test_with_nothing_running_status_says_so_and_exits_0(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    assert "Nothing is running" in status(world, capsys)


def test_after_a_batch_ends_status_says_nothing_is_running(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    assert world.run("run", str(BATCH)) == 0

    out = status(world, capsys)

    assert "Nothing is running" in out
    assert "#10" not in out


def test_a_runner_that_is_gone_leaves_nothing_running(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    gone = subprocess.Popen(["true"])
    gone.wait()
    write_status(
        world,
        f"batch-{BATCH}",
        {"1": lane_state(10, "review", 1, "Read(README.md)", (5, 5, 0.1))},
        gone.pid,
    )

    out = status(world, capsys)

    assert "Nothing is running" in out
    assert "#10" not in out
