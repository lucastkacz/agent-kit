"""A re-run leaves alone a lane issue whose PR waits for the owner (#100, medium tests)."""

from __future__ import annotations

import json

from conftest import World, git
from test_batch import done, pr_for
from test_batch_rerun import BATCH, calls_for, close_issue, summary

# A change to CI is high risk, so its PR waits for the owner (see `test_batch.py`).
HIGH_RISK_WORK = {**done(), "files": [".github/workflows/ci.yml"]}
EARLIER = "its PR has waited for the owner since an earlier run"


def wait_for_the_owner(world: World) -> None:
    """A first run whose lane's only issue, #10, ends with its PR waiting for the owner."""
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, HIGH_RISK_WORK)
    world.run("run", str(BATCH))
    assert pr_for(world, 10)["labels"] == ["risk:high"]


def add_open_pr(world: World, number: int, branch: str) -> None:
    """An open PR on the branch without `risk:high`, as an armed merge that didn't land."""
    state = world.gh()
    state["prs"][str(number)] = {
        "number": number,
        "branch": branch,
        "base": "master",
        "title": "feat: a thing",
        "body": "Closes #10",
        "state": "OPEN",
        "labels": [],
        "comments": [],
        "armed": None,
        "views": [],
    }
    world.gh_state.write_text(json.dumps(state))


def needs_the_owner(text: str) -> str:
    return text[text.index("### Needs the owner") :]


def test_a_rerun_does_no_new_work_on_an_issue_whose_pr_waits_for_the_owner(world: World) -> None:
    wait_for_the_owner(world)
    pr = pr_for(world, 10)
    head = git(world.origin, "rev-parse", pr["branch"])
    runs = len(world.claude_calls())

    assert world.run("run", str(BATCH)) == 0

    assert len(world.claude_calls()) == runs, "the re-run ran Claude on #10 again"
    assert git(world.origin, "rev-parse", pr["branch"]) == head, "the re-run pushed to #10's PR"
    assert pr_for(world, 10)["comments"] == pr["comments"], "the re-run commented on #10's PR"


def test_a_rerun_summary_reports_the_issue_as_waiting_for_the_owner_with_its_pr(
    world: World,
) -> None:
    wait_for_the_owner(world)
    pr = pr_for(world, 10)["number"]

    world.run("run", str(BATCH))

    rerun = summary(world)
    assert f"| #10 | waiting for the owner | #{pr} |" in rerun
    assert f"- #{pr}: waiting for the owner. {EARLIER}." in needs_the_owner(rerun)


def test_a_rerun_of_a_lane_stops_again_at_the_pr_that_waits_for_the_owner(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_issue(12)
    world.add_batch(BATCH, "Lane 1: #10, #11, #12\n")
    world.script("implement", 11, HIGH_RISK_WORK)
    world.run("run", str(BATCH))
    close_issue(world, 10)
    ten, eleven = pr_for(world, 10)["number"], pr_for(world, 11)["number"]

    world.run("run", str(BATCH))

    rerun = summary(world)
    assert f"| #10 | merged | #{ten} |" in rerun
    assert f"| #11 | waiting for the owner | #{eleven} |" in rerun
    assert "| #12 | deferred | - |" in rerun
    assert f"- #{eleven}: waiting for the owner. {EARLIER}." in needs_the_owner(rerun)
    assert len(calls_for(world, "implement", 11)) == 1, "#11 was implemented again"
    assert calls_for(world, "implement", 12) == [], "#12 builds on #11, which hasn't merged"


def test_an_issue_whose_open_pr_isnt_high_risk_is_still_implemented(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    add_open_pr(world, 50, "10-issue-10")

    world.run("run", str(BATCH))

    assert len(calls_for(world, "implement", 10)) == 1
    assert world.gh()["prs"]["50"]["armed"], "#10's PR wasn't armed"
    assert "| #10 | merged | #50 |" in summary(world)
