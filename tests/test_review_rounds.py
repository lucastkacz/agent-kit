"""A pull request's review rounds converge (#74, medium tests).

Each re-review gets what the earlier rounds found. From the third review of a branch on, a new
medium finding that isn't a regression is filed as an issue instead of blocking.
"""

from __future__ import annotations

from typing import Any

from batch_runs import APPROVED, BATCH
from conftest import World
from review_rounds import CRASHES, DROPS_A_LINE, SLOW, changes, finding, ship_rounds

BROKE_A_FIX = finding("medium", "regression", "a.py:4", "The fix broke the header line.")


def review_prompts(world: World, issue: int) -> list[str]:
    calls = [c for c in world.claude_calls() if c["kind"] == "review" and c["number"] == issue]
    return [call["argv"][call["argv"].index("-p") + 1] for call in calls]


def filed(world: World) -> list[dict[str, Any]]:
    """The issues the runner opened, beyond the one being worked on."""
    return [issue for number, issue in world.gh()["issues"].items() if number != "10"]


def test_a_re_review_in_ship_carries_the_earlier_rounds_findings(world: World) -> None:
    ship_rounds(world, changes(DROPS_A_LINE), APPROVED)

    first, second = review_prompts(world, 10)
    for text in (DROPS_A_LINE["problem"], DROPS_A_LINE["location"], DROPS_A_LINE["suggestion"]):
        assert text not in first, first
        assert text in second, second


def test_a_re_review_in_a_batch_carries_the_earlier_rounds_findings(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, changes(CRASHES), APPROVED)

    world.run("run", str(BATCH))

    first, second = review_prompts(world, 10)
    for text in (CRASHES["problem"], CRASHES["location"], CRASHES["suggestion"]):
        assert text not in first, first
        assert text in second, second


def test_from_the_third_review_a_new_medium_finding_is_filed_and_doesnt_block(
    world: World,
) -> None:
    codes = ship_rounds(world, changes(CRASHES), changes(DROPS_A_LINE), changes(SLOW))

    assert codes == [2, 2, 0]
    pr = next(iter(world.gh()["prs"].values()))
    assert pr["armed"]
    [issue] = filed(world)
    assert SLOW["problem"] in issue["title"] + issue["body"]
    assert "#10" in issue["body"]
    assert "ready" not in issue["labels"]


def test_before_the_third_review_a_new_medium_finding_still_blocks(world: World) -> None:
    codes = ship_rounds(world, changes(CRASHES), changes(DROPS_A_LINE))

    assert codes == [2, 2]
    assert world.gh()["prs"] == {}
    assert filed(world) == []


def test_from_the_third_review_a_high_finding_still_blocks_beside_a_filed_one(
    world: World,
) -> None:
    codes = ship_rounds(world, changes(DROPS_A_LINE), changes(BROKE_A_FIX), changes(CRASHES, SLOW))

    assert codes == [2, 2, 2]
    assert world.gh()["prs"] == {}
    [issue] = filed(world)
    assert SLOW["problem"] in issue["title"] + issue["body"]
    assert CRASHES["problem"] not in issue["title"] + issue["body"]


def test_from_the_third_review_a_regression_still_blocks(world: World) -> None:
    codes = ship_rounds(world, changes(CRASHES), changes(DROPS_A_LINE), changes(BROKE_A_FIX))

    assert codes == [2, 2, 2]
    assert world.gh()["prs"] == {}
    assert filed(world) == []
