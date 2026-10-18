"""A batch keeps the Mac awake, or says at the start that it can't (#29)."""

from __future__ import annotations

import os

import pytest

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
