"""A re-run finds an issue's merged PR from how GitHub closed the issue (#66)."""

from __future__ import annotations

import json

from agent_batch.core.model import Closure
from agent_batch.shell.github import closure_of
from conftest import World
from test_batch_rerun import BATCH, calls_for, stop_after_the_first_issue, summary

REPOSITORY = "https://github.com/owner/project"


def edit_issue(world: World, number: int, **fields: str) -> None:
    state = world.gh()
    state["issues"][str(number)].update(fields)
    world.gh_state.write_text(json.dumps(state))


def test_an_issue_retitled_after_its_merge_still_counts_as_merged(world: World) -> None:
    stop_after_the_first_issue(world)
    edit_issue(world, 10, title="A clearer title for issue 10")

    world.run("run", str(BATCH))

    assert "| #10 | merged |" in summary(world)
    assert len(calls_for(world, "implement", 11)) == 2


def test_an_issue_closed_as_not_planned_stops_its_lane_despite_a_merged_pr(world: World) -> None:
    stop_after_the_first_issue(world)
    edit_issue(world, 10, state_reason="NOT_PLANNED")

    world.run("run", str(BATCH))

    rerun = summary(world)
    assert "| #10 | skipped |" in rerun
    assert "deferred 1" in rerun
    assert len(calls_for(world, "implement", 11)) == 1


def test_only_the_prs_of_the_issues_own_repository_close_it() -> None:
    raw = {
        "url": f"{REPOSITORY}/issues/10",
        "stateReason": "COMPLETED",
        "closedByPullRequestsReferences": [
            {"number": 4, "url": "https://github.com/someone/else/pull/4"},
            {"number": 12, "url": f"{REPOSITORY}/pull/12"},
        ],
    }

    assert closure_of(raw) == Closure(reason="COMPLETED", prs=(12,))
