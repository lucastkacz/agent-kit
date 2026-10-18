"""A batch keeps the Mac awake, or says at the start that it can't (#29)."""

from __future__ import annotations

import io
import json
import os

import pytest

from agent_batch.shell import system
from agent_hooks import session_start
from conftest import World

BATCH = 1


def _run_one_issue(world: World) -> int:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    return world.run("run", str(BATCH))


def test_a_batch_holds_off_both_idle_and_system_sleep_while_it_runs(world: World) -> None:
    assert _run_one_issue(world) == 0

    [flags] = world.caffeinate_calls()
    assert "-i" in flags, "idle sleep isn't held off"
    assert "-s" in flags, "system sleep isn't held off"
    assert flags[flags.index("-w") + 1] == str(os.getpid())


def test_a_batch_on_battery_says_the_mac_may_sleep_unless_plugged_in_and_still_runs(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.on_battery()

    assert _run_one_issue(world) == 0

    said = capsys.readouterr().out.lower()
    assert "battery" in said
    assert "may sleep" in said
    assert "plugged in" in said
    [pr] = world.gh()["prs"].values()
    assert pr["armed"], "the batch should have run on battery anyway"


def test_a_batch_on_ac_power_says_nothing_about_the_battery(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run_one_issue(world) == 0

    assert "battery" not in capsys.readouterr().out.lower()


def test_a_refused_batch_on_battery_leaves_no_batch_running_for_the_next_session(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.on_battery()
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n", author="someone-else")

    assert world.run("run", str(BATCH)) == 1

    payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(world.project)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert session_start.main() == 0
    assert "is running, or stopped halfway" not in out.getvalue()


def test_a_pmset_that_cant_run_counts_as_not_on_battery(world: World) -> None:
    (world.root / "bin" / "pmset").write_text("#!/nonexistent/sh\n")

    assert not system.on_battery()


def test_a_pmset_that_hangs_counts_as_not_on_battery(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    (world.root / "bin" / "pmset").write_text("#!/bin/sh\nexec sleep 5\n")
    monkeypatch.setattr(system, "PMSET_TIMEOUT", 0.1)

    assert not system.on_battery()
