"""A finding that comes after planning closed a PR's follow-up issue opens a new one (#136)."""

from __future__ import annotations

import json

from conftest import World
from test_found_work_one_follow_up import TRIMS, follow_ups, issue_found
from test_review_rounds import CRASHES, DROPS_A_LINE, SLOW, changes, commit, ship, start_branch


def close(world: World, number: str) -> None:
    state = world.gh()
    state["issues"][number]["state"] = "CLOSED"
    world.gh_state.write_text(json.dumps(state))


def test_a_finding_after_the_follow_up_closed_files_a_new_follow_up(world: World) -> None:
    world.add_issue(10)
    world.script(
        "review",
        10,
        changes(CRASHES),
        changes(DROPS_A_LINE),
        changes(CRASHES, SLOW),
        changes(TRIMS),
    )
    body = start_branch(world)
    codes = [ship(world, body)]
    for index in range(1, 4):
        commit(world, f"fix_{index}.txt")
        if index == 3:
            [first] = [issue["number"] for issue in follow_ups(world)]
            close(world, str(first))
        codes.append(ship(world, body))

    assert codes == [2, 2, 2, 0]
    old, new = sorted(follow_ups(world), key=lambda issue: int(issue["number"]))
    assert old["comments"] == []
    assert TRIMS["problem"] in new["body"]
    assert new["state"] == "OPEN"
    assert len(issue_found(world)) == 2
