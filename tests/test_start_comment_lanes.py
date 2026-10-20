"""The start comment counts the lanes that run at once, not more than the plan has (#198)."""

from __future__ import annotations

from batch_runs import BATCH
from conftest import World


def test_the_start_comment_counts_no_more_lanes_at_a_time_than_the_plan_has(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10\nLane 2: #11\n")

    assert world.run("run", "--lanes", "4", "--max-issues", "1", str(BATCH)) == 0

    assert "**Lanes at a time:** 2" in world.gh()["issues"][str(BATCH)]["comments"][0]
