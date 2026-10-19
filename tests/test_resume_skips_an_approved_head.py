"""A resumed batch doesn't review again a head that an approved review already read (#195).

The tests run `agent-batch run` twice with real git and fake `gh` and `claude` (medium tests): the
first run's push fails at GitHub after an approved review, as in batch #187.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agent_batch.shell.git import Git
from agent_batch.shell.proc import CommandError
from conftest import World

BATCH = 1
ISSUE = 10
PUSH_500 = "`git push --quiet` failed: remote: Internal Server Error"


def fail_the_first_pushes(monkeypatch: pytest.MonkeyPatch, times: int) -> list[str]:
    """Makes the first `times` pushes fail with a server error; returns the pushed branches."""
    original = Git.push
    pushed: list[str] = []

    def push(self: Git, worktree: Any, branch: str) -> None:
        pushed.append(branch)
        if len(pushed) <= times:
            raise CommandError(PUSH_500)
        original(self, worktree, branch)

    monkeypatch.setattr(Git, "push", push)
    return pushed


def unblock(world: World, number: int) -> None:
    """Takes the `blocked` label off, as the owner does before resuming the batch."""
    state = world.gh()
    labels: list[str] = state["issues"][str(number)]["labels"]
    state["issues"][str(number)]["labels"] = [label for label in labels if label != "blocked"]
    world.gh_state.write_text(json.dumps(state))


def calls_for(world: World, kind: str) -> list[dict[str, Any]]:
    return [c for c in world.claude_calls() if c["kind"] == kind and c["number"] == ISSUE]


def the_pr(world: World) -> dict[str, Any]:
    prs = [pr for pr in world.gh()["prs"].values() if pr["branch"].startswith(f"{ISSUE}-")]
    assert len(prs) == 1, prs
    pr: dict[str, Any] = prs[0]
    return pr


def fail_after_the_review(world: World, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """A first run whose approved branch never reaches GitHub, unblocked for the resume."""
    world.add_issue(ISSUE)
    world.add_batch(BATCH, f"Lane 1: #{ISSUE}\n")
    pushed = fail_the_first_pushes(monkeypatch, 3)
    world.run("run", str(BATCH))
    assert len(calls_for(world, "review")) == 1
    assert not world.gh()["prs"]
    unblock(world, ISSUE)
    return pushed


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
