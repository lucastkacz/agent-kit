"""A PR's found work lands in one follow-up issue, not one issue per item (#136, medium tests)."""

from __future__ import annotations

from batch_runs import APPROVED, BATCH, CHANGES, done
from conftest import World
from follow_ups import CONFLICTING, DATES, TRIMS, follow_ups, issue_found
from review_rounds import CRASHES, DROPS_A_LINE, SLOW, changes, ship_rounds

CACHE = {"kind": "task", "title": "Cache the parse", "body": "It parses each file twice."}
NAMES = {"kind": "idea", "title": "Rename the lanes", "body": "Their numbers say little."}


def run_with_found(world: World, *found: dict[str, str]) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, done(found=list(found)))
    world.run("run", str(BATCH))


def test_several_found_items_become_one_follow_up_issue_and_one_event(world: World) -> None:
    run_with_found(world, DATES, CACHE, NAMES)

    [issue] = follow_ups(world)
    for item in (DATES, CACHE, NAMES):
        assert item["title"] in issue["body"], issue["body"]
        assert item["body"] in issue["body"], issue["body"]
    assert "Found while working on #10." in issue["body"]
    assert "#10" in issue["title"]
    assert "ready" not in issue["labels"]
    [event] = issue_found(world)
    assert (event["issue"], event["found"]) == (10, issue["number"])


def test_one_found_item_becomes_one_issue_as_today(world: World) -> None:
    run_with_found(world, DATES)

    [issue] = follow_ups(world)
    assert issue["title"] == DATES["title"]
    assert issue["labels"] == ["idea"]
    assert DATES["body"] in issue["body"]
    assert "Found while working on #10." in issue["body"]
    [event] = issue_found(world)
    assert event["found"] == issue["number"]


def test_no_found_items_file_no_issue(world: World) -> None:
    run_with_found(world)

    assert follow_ups(world) == []
    assert issue_found(world) == []


def test_the_follow_up_issue_takes_the_most_severe_kind_as_its_label(world: World) -> None:
    run_with_found(world, DATES, CACHE, NAMES)

    [issue] = follow_ups(world)
    assert issue["labels"] == ["task"]


def test_a_third_reviews_finding_joins_the_prs_follow_up_issue_as_a_comment(
    world: World,
) -> None:
    """The implementer's found work opens the issue; the review after a conflict comments on it."""
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {**done(), "files": ["shared.txt"]})
    world.script("fix", 10, done(found=[DATES, CACHE]))
    world.script("review", 10, CHANGES, APPROVED, changes(SLOW))
    world.pr_views("10-issue-10", CONFLICTING)

    world.run("run", str(BATCH))

    [issue] = follow_ups(world)
    assert DATES["title"] in issue["body"]
    assert SLOW["problem"] not in issue["body"]
    assert any(SLOW["problem"] in comment for comment in issue["comments"]), issue["comments"]
    assert len(issue_found(world)) == 1


def test_later_reviews_findings_join_the_follow_up_issue_the_third_review_opened(
    world: World,
) -> None:
    codes = ship_rounds(
        world, changes(CRASHES), changes(DROPS_A_LINE), changes(CRASHES, SLOW), changes(TRIMS)
    )

    assert codes == [2, 2, 2, 0]
    [issue] = follow_ups(world)
    assert SLOW["problem"] in issue["body"]
    assert any(TRIMS["problem"] in comment for comment in issue["comments"]), issue["comments"]
    assert TRIMS["problem"] not in issue["body"]
    assert len(issue_found(world)) == 1
