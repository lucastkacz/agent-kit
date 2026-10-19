"""A `systemd-inhibit` that can't take its lock holds nothing; an unreadable supply is skipped."""

from __future__ import annotations

import sys

import pytest

from agent_batch.shell import system
from conftest import World

# What `systemd-inhibit` does without a system bus: it says why on stderr and exits at once.
FAILING_INHIBIT = """#!/bin/sh
echo "Failed to inhibit: Failed to connect to bus: No such file or directory" >&2
exit 1
"""


def _failing_inhibit(world: World) -> None:
    fake = world.root / "bin" / "systemd-inhibit"
    fake.write_text(FAILING_INHIBIT)
    fake.chmod(0o755)


def test_a_systemd_inhibit_that_fails_doesnt_count_as_keeping_the_computer_awake(
    world: World,
) -> None:
    _failing_inhibit(world)

    assert system.keep_awake("linux") is None


def test_where_systemd_inhibit_fails_the_batch_says_so_at_the_start_and_still_runs(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    world.linux_power(mains_online=True)
    _failing_inhibit(world)
    world.add_issue(10)
    world.add_batch(1, "Lane 1: #10\n")

    assert world.run("run", "1") == 0

    said = capsys.readouterr().out
    assert "can't keep the computer awake" in said
    assert said.index("can't keep the computer awake") < said.index("issue_started")
    [pr] = world.gh()["prs"].values()
    assert pr["armed"], "the batch should have run anyway"


def test_a_supply_whose_type_cant_be_read_is_skipped(world: World) -> None:
    world.linux_power(mains_online=False)
    # A folder where the file should be can't be read as text, as a vendor supply may not be.
    (world.power_supplies / "ucsi-source-psy-0" / "type").mkdir(parents=True)

    assert system.on_battery("linux")
