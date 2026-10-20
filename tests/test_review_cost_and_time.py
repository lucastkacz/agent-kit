"""Each review logs its run's cost and time, so an acceptance can count them (#76)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from batch_runs import BATCH
from conftest import World, git

CHANGES = {
    "verdict": "changes",
    "findings": [
        {
            "severity": "high",
            "origin": "new",
            "location": "a.py:3",
            "problem": "It crashes.",
            "suggestion": "Guard it.",
        }
    ],
}


@pytest.fixture(autouse=True)
def wall_clock(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """The computer's clock, which a fake run's `slept` moves on, so a review takes known time."""
    awake = time.time
    monkeypatch.setattr(time, "time", lambda: awake() + world.slept())


def reviews(log: Path) -> list[tuple[bool, float, object]]:
    """Each `reviewed` event's verdict, cost in dollars and seconds."""
    records = [json.loads(line) for line in log.read_text().splitlines()]
    return [
        (r["approved"], r["cost_usd"], r["seconds"]) for r in records if r["event"] == "reviewed"
    ]


def test_each_review_in_a_batch_logs_its_cost_and_seconds_approved_or_not(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script(
        "review",
        10,
        {"output": CHANGES, "cost": 0.25, "slept": 600},
        {"cost": 0.5, "slept": 1200},
    )

    world.run("run", str(BATCH))

    logged = reviews(world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl")
    assert logged == [
        (False, 0.25, pytest.approx(600, abs=30)),
        (True, 0.5, pytest.approx(1200, abs=30)),
    ]


def test_each_review_in_ship_logs_its_cost_and_seconds_approved_or_not(world: World) -> None:
    world.add_issue(10)
    world.script(
        "review",
        10,
        {"output": CHANGES, "cost": 0.25, "slept": 600},
        {"cost": 0.5, "slept": 1200},
    )
    git(world.project, "switch", "--quiet", "--create", "10-add-feature")
    (world.project / "feature.txt").write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: work")
    body = world.root / "body.md"
    body.write_text("Adds the feature.\n")
    ship = ("ship", "10", "--title", "feat: add the feature", "--body-file", str(body))

    assert world.run(*ship) == 2
    assert world.run(*ship) == 0

    logged = reviews(world.project / ".agent-batch" / "ship-10" / "events.jsonl")
    assert logged == [
        (False, 0.25, pytest.approx(600, abs=30)),
        (True, 0.5, pytest.approx(1200, abs=30)),
    ]
