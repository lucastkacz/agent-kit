"""How many lanes run at a time (#3)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import plan
from agent_batch.core.plan import BatchPlan, PlanError
from conftest import World

COUNTS = st.one_of(st.none(), st.integers(min_value=1, max_value=9))


def test_the_batch_issue_sets_how_many_lanes_run_at_a_time() -> None:
    assert plan.parse_plan("Lane 1: #1\nLanes: 3\n").lanes_at_once == 3
    assert plan.parse_plan("Lane 1: #1\n").lanes_at_once is None


def test_a_lane_count_under_one_in_the_issue_is_refused() -> None:
    with pytest.raises(PlanError, match="at least 1"):
        plan.parse_plan("Lane 1: #1\nLanes: 0\n")


@given(COUNTS, COUNTS, st.integers(min_value=1, max_value=9))
def test_the_flag_wins_over_the_issue_which_wins_over_the_default(
    requested: int | None, planned: int | None, default: int
) -> None:
    batch = BatchPlan(lanes=((1,),), lanes_at_once=planned)
    chosen = plan.concurrency(requested, batch, default)
    assert chosen == next(n for n in (requested, planned, default) if n is not None)


def test_the_start_comment_says_how_many_lanes_run_at_a_time(world: World) -> None:
    world.add_issue(10)
    world.add_batch(1, "Lane 1: #10\nLanes: 1\n")

    world.run("run", "1")

    assert "**Lanes at a time:** 1" in world.gh()["issues"]["1"]["comments"][0]


def test_the_flag_refuses_a_count_under_one(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_batch(1, "Lane 1: #10\n")

    with pytest.raises(SystemExit) as exited:
        world.run("run", "--lanes", "0", "1")

    assert exited.value.code == 2
    assert "at least 1" in capsys.readouterr().err
