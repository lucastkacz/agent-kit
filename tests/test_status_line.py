"""`agent-batch status --line`: the batch's progress under Claude Code's prompt (#108)."""

from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from conftest import World, git

ROOT = Path(__file__).resolve().parent.parent
USAGE = ROOT / "docs" / "usage.md"
SETTINGS = ROOT / ".claude" / "settings.json"
PLUGIN_HOOKS = ROOT / "plugin" / "hooks" / "hooks.json"


def lane(
    issue: int, step: str, review_round: int, rounds: int, minutes: float
) -> dict[str, object]:
    now = time.time()
    return {
        "issue": issue,
        "step": step,
        "round": review_round,
        "rounds": rounds,
        "action": "Read(README.md)",
        "action_time": now - 5,
        "started": now - minutes * 60,
        "cost_usd": 0.5,
    }


def write_status(world: World, run: str, lanes: dict[str, object]) -> None:
    folder = world.project / ".agent-batch" / run
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "status.json").write_text(json.dumps({"pid": os.getpid(), "lanes": lanes}))


def a_running_batch_and_ship(world: World) -> None:
    write_status(
        world,
        "batch-1",
        {"1": lane(75, "review", 2, 2, 30), "2": lane(66, "implementation", 0, 2, 12.5)},
    )
    write_status(world, "ship-79", {"0": lane(79, "review", 1, 1, 4)})


def status_line(
    world: World, cwd: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> str:
    """What `agent-batch status --line` prints, given Claude Code's JSON with `cwd` on stdin."""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(cwd)})))
    capsys.readouterr()
    assert world.run("status", "--line") == 0
    out = capsys.readouterr().out
    assert len(out.splitlines()) == 1, out
    return out.strip()


def test_status_line_prints_each_running_lane_and_ship_with_its_issue_step_and_round(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    a_running_batch_and_ship(world)

    line = status_line(world, world.project, capsys, monkeypatch)

    assert line == "L1 #75 review 2/2 · L2 #66 implement 12m · ship #79 review 1/1"


def test_with_nothing_running_the_status_line_shows_the_projects_branch_and_exits_0(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert "master" in status_line(world, world.project, capsys, monkeypatch)

    git(world.project, "switch", "--quiet", "--create", "12-add-feature")

    line = status_line(world, world.project, capsys, monkeypatch)
    assert "12-add-feature" in line
    assert "#" not in line


def test_the_status_line_reads_the_sessions_directory_from_stdin_not_its_own(
    world: World,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a_running_batch_and_ship(world)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    inside = world.project / "src"
    inside.mkdir()

    line = status_line(world, inside, capsys, monkeypatch)

    assert "L1 #75 review 2/2" in line


def test_from_a_lane_worktree_the_status_line_finds_the_projects_state(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = world.project / ".agent-batch" / "worktrees" / "lane-1"
    git(world.project, "worktree", "add", "--quiet", "-b", "75-a-lane", str(worktree))

    assert "75-a-lane" in status_line(world, worktree, capsys, monkeypatch)

    a_running_batch_and_ship(world)

    line = status_line(world, worktree, capsys, monkeypatch)
    assert line == "L1 #75 review 2/2 · L2 #66 implement 12m · ship #79 review 1/1"


def test_the_status_line_runs_no_command_and_opens_no_connection(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No `gh`, no network, and no `git`, which can wait on a lock: it reads files alone."""

    def refused(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"the status line started something: {args!r} {kwargs!r}")

    for name in ("Popen", "run", "check_output", "call"):
        monkeypatch.setattr(subprocess, name, refused)
    monkeypatch.setattr(os, "system", refused)
    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, refused)

    assert "master" in status_line(world, world.project, capsys, monkeypatch)
    a_running_batch_and_ship(world)
    assert "L1 #75" in status_line(world, world.project, capsys, monkeypatch)


def test_the_usage_page_says_the_plugin_shows_the_progress_under_the_prompt_and_its_version() -> (
    None
):
    text = " ".join(USAGE.read_text(encoding="utf-8").split())

    assert "under the prompt" in text
    assert "agent-batch status --line" in text
    assert "2.1.287 or later" in text


def test_this_repositorys_settings_keep_only_the_marketplace_and_the_plugin() -> None:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert set(settings) == {"extraKnownMarketplaces", "enabledPlugins"}


def test_the_plugin_loads_a_mod_that_shows_the_status_line() -> None:
    hooks = json.loads(PLUGIN_HOOKS.read_text(encoding="utf-8"))
    modules = hooks.get("modules")
    assert isinstance(modules, list)
    assert len(modules) == 1, modules
    source = (PLUGIN_HOOKS.parent / modules[0]).read_text(encoding="utf-8")

    assert "$.ui.status" in source
    assert "'status', '--line'" in source
