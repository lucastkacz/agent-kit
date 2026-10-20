"""`agent-batch run` again on a batch whose lanes already merged some issues (#66, medium tests)."""

from __future__ import annotations

import json

from batch_runs import BATCH, calls_for, close_issue, stop_after_the_first_issue, summary
from conftest import World


def add_closed_pr(world: World, number: int, branch: str) -> None:
    """A PR on the branch that was closed without merging."""
    state = world.gh()
    state["prs"][str(number)] = {
        "number": number,
        "branch": branch,
        "base": "master",
        "title": "feat: a thing",
        "body": "Closes #10",
        "state": "CLOSED",
        "labels": [],
        "comments": [],
        "armed": None,
        "views": [],
    }
    world.gh_state.write_text(json.dumps(state))


def test_a_rerun_goes_on_to_the_next_issue_after_one_that_already_merged(world: World) -> None:
    stop_after_the_first_issue(world)

    assert world.run("run", str(BATCH)) == 0

    assert len(calls_for(world, "implement", 10)) == 1, "#10 merged; it isn't implemented again"
    assert len(calls_for(world, "implement", 11)) == 2
    eleven = [pr for pr in world.gh()["prs"].values() if pr["branch"].startswith("11-")]
    assert len(eleven) == 1
    assert eleven[0]["armed"], "#11's merge wasn't armed"


def test_a_rerun_summary_reports_the_already_merged_issue_as_merged(world: World) -> None:
    stop_after_the_first_issue(world)
    ten = next(pr for pr in world.gh()["prs"].values() if pr["branch"].startswith("10-"))

    world.run("run", str(BATCH))

    rerun = summary(world)
    assert f"| #10 | merged | #{ten['number']} |" in rerun
    assert "merged 2" in rerun
    assert "skipped" not in rerun
    assert "deferred" not in rerun


def test_a_closed_issue_without_a_merged_pr_still_stops_its_lane(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    close_issue(world, 10)
    add_closed_pr(world, 50, "10-issue-10")

    world.run("run", str(BATCH))

    assert world.claude_calls() == []
    rerun = summary(world)
    assert "| #10 | skipped |" in rerun
    assert "skipped 1" in rerun
    assert "deferred 1" in rerun
