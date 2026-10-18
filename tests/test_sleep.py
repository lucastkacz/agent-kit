"""The batch's times count the time the computer slept (#28)."""

from __future__ import annotations

import re
import time

import pytest

from conftest import World

BATCH = 1
TWO_HOURS = 7200


@pytest.fixture(autouse=True)
def wall_clock(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """The computer's clock, which goes on while it sleeps, as a Mac's does."""
    awake = time.time
    monkeypatch.setattr(time, "time", lambda: awake() + world.slept())


def summary(world: World) -> str:
    comment: str = world.gh()["issues"][str(BATCH)]["comments"][-1]
    return comment


def test_the_summary_minutes_include_the_time_the_computer_slept(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {"slept": TWO_HOURS})

    world.run("run", str(BATCH))

    assert re.search(r"^\| #10 \| merged \|.*\| 120 \|$", summary(world), re.MULTILINE)
    assert "**Time:** 120 min" in summary(world)


@pytest.mark.parametrize(
    ("budget", "flags"),
    [("Budget: 1 hour\n", ()), ("", ("--max-hours", "1"))],
    ids=["budget line", "max-hours flag"],
)
def test_no_issue_starts_once_the_budget_hours_passed_on_the_clock(
    world: World, budget: str, flags: tuple[str, ...]
) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, f"Lane 1: #10, #11\n{budget}")
    world.script("implement", 10, {"slept": TWO_HOURS})

    world.run("run", *flags, str(BATCH))

    assert {call["number"] for call in world.claude_calls()} == {10}
    assert "merged 1 · deferred 1" in summary(world)
