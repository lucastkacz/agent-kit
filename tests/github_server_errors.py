"""What tests of GitHub's server errors share: the errors GitHub answers, and the issue's end."""

from __future__ import annotations

from typing import Any

import pytest

from agent_batch.shell.git import Git
from agent_batch.shell.proc import CommandError
from batch_runs import BATCH, calls_for, events, unblock
from conftest import World

ISSUE = 10
PUSH_500 = "`git push --quiet` failed: remote: Internal Server Error"
PR_GRAPHQL = (
    "`gh pr create` failed: GraphQL: Something went wrong while executing your query. This may "
    "be the result of a timeout, or it could be a GitHub bug. Please include "
    "`E322:12220F:324587:4ED219:6AD64F5E` when reporting this issue."
)


def finished(world: World) -> dict[str, Any]:
    return next(
        e for e in events(world, BATCH) if e["event"] == "issue_finished" and e["issue"] == ISSUE
    )


def one_issue(world: World) -> None:
    world.add_issue(ISSUE)
    world.add_batch(BATCH, f"Lane 1: #{ISSUE}\n")


def flaky(
    monkeypatch: pytest.MonkeyPatch,
    owner: type,
    name: str,
    errors: list[str],
    only: int | None = None,
) -> list[tuple[Any, ...]]:
    """Makes `owner.name` fail with each of `errors` in turn, then work; returns its calls.

    With `only`, just the calls whose first argument is `only` count and fail.
    """
    original = getattr(owner, name)
    calls: list[tuple[Any, ...]] = []
    left = list(errors)

    def call(self: object, *args: Any) -> Any:
        if only is not None and args[0] != only:
            return original(self, *args)
        calls.append(args)
        if left:
            raise CommandError(left.pop(0))
        return original(self, *args)

    monkeypatch.setattr(owner, name, call)
    return calls


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


def fail_after_the_review(world: World, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """A first run whose approved branch never reaches GitHub, unblocked for the resume."""
    world.add_issue(ISSUE)
    world.add_batch(BATCH, f"Lane 1: #{ISSUE}\n")
    pushed = fail_the_first_pushes(monkeypatch, 3)
    world.run("run", str(BATCH))
    assert len(calls_for(world, "review", ISSUE)) == 1
    assert not world.gh()["prs"]
    unblock(world, ISSUE)
    return pushed
