"""`agent-batch status --line` prints nothing in a project that doesn't enable agent-kit (#171)."""

from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path

import pytest

from conftest import World, git

ENABLED = '{"enabledPlugins": {"agent-kit@agent-kit": true}}\n'


def a_running_batch(world: World) -> None:
    folder = world.project / ".agent-batch" / "batch-1"
    folder.mkdir(parents=True, exist_ok=True)
    now = time.time()
    lane = {
        "issue": 75,
        "step": "review",
        "round": 2,
        "rounds": 2,
        "action": "Read(README.md)",
        "action_time": now - 5,
        "started": now - 30 * 60,
        "cost_usd": 0.5,
    }
    status = {"pid": os.getpid(), "lanes": {"1": lane}}
    (folder / "status.json").write_text(json.dumps(status))


def printed(
    cwd: Path, world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> str:
    """All that `agent-batch status --line` prints, given Claude Code's JSON with `cwd`."""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(cwd)})))
    capsys.readouterr()
    assert world.run("status", "--line") == 0
    return capsys.readouterr().out


def settings(world: World, name: str, text: str | None) -> None:
    path = world.project / ".claude" / name
    if text is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(text)


@pytest.mark.parametrize(
    "text",
    [None, "{}\n", '{"enabledPlugins": {"agent-kit@agent-kit": false}}\n', "not json"],
    ids=["no settings", "no plugins", "agent-kit turned off", "unreadable settings"],
)
def test_where_the_project_doesnt_enable_agent_kit_the_status_line_prints_nothing(
    text: str | None,
    world: World,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings(world, "settings.json", text)

    assert printed(world.project, world, capsys, monkeypatch) == ""

    a_running_batch(world)
    assert printed(world.project, world, capsys, monkeypatch) == ""


def test_from_a_worktree_the_status_line_reads_the_main_checkouts_settings(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = world.project / ".agent-batch" / "worktrees" / "lane-1"
    git(world.project, "worktree", "add", "--quiet", "-b", "75-a-lane", str(worktree))
    settings(world, "settings.json", "{}\n")
    a_running_batch(world)

    assert printed(worktree, world, capsys, monkeypatch) == ""


def test_where_the_project_enables_agent_kit_the_status_line_is_as_before(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    settings(world, "settings.json", ENABLED)

    assert printed(world.project, world, capsys, monkeypatch) == "nothing running · master\n"

    a_running_batch(world)
    assert printed(world.project, world, capsys, monkeypatch) == "L1 #75 review 2/2\n"


def test_the_projects_local_settings_can_enable_agent_kit_for_the_status_line(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    settings(world, "settings.json", None)
    settings(world, "settings.local.json", ENABLED)
    a_running_batch(world)

    assert printed(world.project, world, capsys, monkeypatch) == "L1 #75 review 2/2\n"
