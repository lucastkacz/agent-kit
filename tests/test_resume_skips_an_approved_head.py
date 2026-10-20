"""A resumed batch doesn't review again a head that an approved review already read (#195).

The tests run `agent-batch run` twice with real git and fake `gh` and `claude` (medium tests): the
first run's push fails at GitHub after an approved review, as in batch #187.
"""

from __future__ import annotations

from typing import Any

import pytest

from batch_runs import BATCH
from conftest import World
from github_server_errors import ISSUE, fail_after_the_review


def calls_for(world: World, kind: str) -> list[dict[str, Any]]:
    return [c for c in world.claude_calls() if c["kind"] == kind and c["number"] == ISSUE]


def the_pr(world: World) -> dict[str, Any]:
    prs = [pr for pr in world.gh()["prs"].values() if pr["branch"].startswith(f"{ISSUE}-")]
    assert len(prs) == 1, prs
    pr: dict[str, Any] = prs[0]
    return pr


def test_a_resume_pushes_an_approved_head_without_another_review(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    pushed = fail_after_the_review(world, monkeypatch)
    # The implementer finds its work done and commits nothing, so the head stays the reviewed one.
    world.script("implement", ISSUE, {}, {"commits": False})

    world.run("run", str(BATCH))

    assert len(calls_for(world, "review")) == 1, "the approved head was reviewed again"
    assert len(pushed) == 4
    assert the_pr(world)["armed"], "the PR's merge wasn't armed"


def test_a_resume_reviews_a_head_that_moved_since_the_approved_review(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    fail_after_the_review(world, monkeypatch)

    world.run("run", str(BATCH))

    assert len(calls_for(world, "review")) == 2
    assert the_pr(world)["armed"], "the PR's merge wasn't armed"
