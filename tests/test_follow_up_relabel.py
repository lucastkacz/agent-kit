"""A bug that joins an idea's follow-up issue makes it a bug (#136, medium tests)."""

from __future__ import annotations

from batch_runs import APPROVED, BATCH, CHANGES, done
from conftest import World
from follow_ups import CONFLICTING, DATES, follow_ups
from review_rounds import SLOW, changes


def test_a_third_reviews_finding_makes_an_idea_follow_up_a_bug(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {**done(), "files": ["shared.txt"]})
    world.script("fix", 10, done(found=[DATES]))
    world.script("review", 10, CHANGES, APPROVED, changes(SLOW))
    world.pr_views("10-issue-10", CONFLICTING)

    world.run("run", str(BATCH))

    [issue] = follow_ups(world)
    assert issue["labels"] == ["bug"]
