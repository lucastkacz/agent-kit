"""The edges #195's review found: the push after a conflict, a PR GitHub created before it failed,
a later review of an approved head, and another error on the last try."""

from __future__ import annotations

from typing import Any

import pytest

from agent_batch.core import rounds
from agent_batch.core.model import Finding
from agent_batch.shell import retry
from agent_batch.shell.git import Git
from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from conftest import World
from test_batch import BATCH, done, pr_for
from test_github_server_errors_retried import PR_GRAPHQL, PUSH_500, finished


def test_the_push_after_a_resolved_conflict_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {**done(), "files": ["shared.txt"]})
    conflict = {"file": "shared.txt", "content": "another lane\n"}
    world.pr_views(
        "10-issue-10", {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": conflict}
    )
    original = Git.push
    pushes: list[str] = []

    def push(self: Git, worktree: Any, branch: str) -> None:
        pushes.append(branch)
        # The first push is `publish`'s; the second, the one after the conflict, fails once.
        if len(pushes) == 2:
            raise CommandError(PUSH_500)
        original(self, worktree, branch)

    monkeypatch.setattr(Git, "push", push)

    world.run("run", str(BATCH))

    assert len(pushes) == 3
    assert finished(world)["outcome"] == "merged"


def test_a_pr_github_created_before_its_graphql_error_is_used_on_the_next_try(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    original = GitHub.create_pr
    creates: list[str] = []

    def create_pr(self: GitHub, branch: str, base: str, title: str, body: str) -> int:
        creates.append(branch)
        original(self, branch, base, title, body)
        raise CommandError(PR_GRAPHQL)

    monkeypatch.setattr(GitHub, "create_pr", create_pr)

    world.run("run", str(BATCH))

    assert len(creates) == 1
    assert finished(world)["outcome"] == "merged"
    assert pr_for(world, 10)["armed"]


def finding(severity: str) -> Finding:
    return Finding(severity, "new", "a.py:1", "A problem.", "A fix.")


def test_a_later_review_of_the_head_that_asks_for_changes_wins_over_its_approval() -> None:
    earlier = (
        rounds.Round(1, "aaa", (), approved=True),
        rounds.Round(2, "aaa", (finding("high"),)),
    )

    assert rounds.approved_findings(earlier, "aaa") is None


def test_another_error_on_the_last_try_is_raised_as_it_is() -> None:
    errors = ["HTTP 502: Bad Gateway", "HTTP 502: Bad Gateway", "HTTP 404: Not Found"]

    def call() -> int:
        raise CommandError(errors.pop(0))

    with pytest.raises(CommandError, match=r"^HTTP 404: Not Found$"):
        retry.retried(call, 0)
    assert not errors
