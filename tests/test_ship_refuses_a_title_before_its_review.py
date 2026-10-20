"""`ship` refuses a `--title` that can't be a PR's before its review, and a lane's implementer
title still falls back to the issue's (#236, medium tests)."""

from __future__ import annotations

import pytest

from batch_runs import BATCH, done, pr_for
from conftest import World
from ship_branches import branch_with_work, only_pr

LONG = "feat: " + " and ".join(["a very long title"] * 5)


@pytest.mark.parametrize(
    ("given", "reason"),
    [
        ("Added the feature", "Conventional Commits"),
        (LONG, "has 111 characters"),
        ("feat: one\nfeat: two", "more than one line"),
    ],
)
def test_a_refused_title_stops_ship_before_its_review_with_why_and_the_limit(
    world: World, capsys: pytest.CaptureFixture[str], given: str, reason: str
) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    code = world.run("ship", "10", "--title", given, "--body-file", str(body))

    assert code != 0
    assert world.claude_calls() == []
    assert world.gh()["prs"] == {}
    err = capsys.readouterr().err
    assert reason in err
    assert "72" in err


def test_a_valid_title_ships_as_the_prs_title(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "fix: keep it", "--body-file", str(body)) == 0

    pr = only_pr(world)
    assert pr["title"] == "fix: keep it"
    assert pr["armed"]


def test_a_lanes_refused_implementer_title_still_falls_back_to_the_issues(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, done(title=LONG))

    assert world.run("run", str(BATCH)) == 0

    pr = pr_for(world, 10)
    assert pr["title"] == "feat: Issue 10"
    assert pr["armed"]
