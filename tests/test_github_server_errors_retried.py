"""A GitHub server error on a push, a PR or `announce` is tried again, up to 3 times (#195).

The tests run `agent-batch run` with real git and fake `gh` and `claude` (medium tests); the waits
between tries are `AGENT_BATCH_POLL_SECONDS`, which the tests set near 0.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agent_batch.shell.git import Git
from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from conftest import World

BATCH = 1
ISSUE = 10
PUSH_500 = "`git push --quiet` failed: remote: Internal Server Error"
PR_GRAPHQL = (
    "`gh pr create` failed: GraphQL: Something went wrong while executing your query. This may "
    "be the result of a timeout, or it could be a GitHub bug. Please include "
    "`E322:12220F:324587:4ED219:6AD64F5E` when reporting this issue."
)
LABEL_502 = "`gh issue edit` failed: HTTP 502: Bad Gateway (https://api.github.com/graphql)"
COMMENT_503 = (
    "`gh issue comment` failed: HTTP 503: Service Unavailable "
    "(https://api.github.com/repos/o/r/issues/10/comments)"
)
PUSH_REJECTED = (
    "`git push --quiet` failed: To github.com:o/r.git\n"
    " ! [rejected]        10-issue-10 -> 10-issue-10 (fetch first)\n"
    "error: failed to push some refs to 'github.com:o/r.git'"
)
PR_REFUSED = (
    "`gh pr create` failed: pull request create failed: GraphQL: No commits between master and "
    "10-issue-10 (createPullRequest)"
)
BLOCKED = {"status": "blocked", "title": "", "pr_body": "", "message": "Which one?", "found": []}


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


def events(world: World) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()]


def finished(world: World) -> dict[str, Any]:
    return next(e for e in events(world) if e["event"] == "issue_finished" and e["issue"] == ISSUE)


def armed(world: World) -> bool:
    prs = [pr for pr in world.gh()["prs"].values() if pr["branch"].startswith(f"{ISSUE}-")]
    return len(prs) == 1 and bool(prs[0]["armed"])


def one_issue(world: World) -> None:
    world.add_issue(ISSUE)
    world.add_batch(BATCH, f"Lane 1: #{ISSUE}\n")


def test_a_push_that_github_fails_twice_passes_on_the_third_try(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    pushes = flaky(monkeypatch, Git, "push", [PUSH_500, PUSH_500])

    world.run("run", str(BATCH))

    assert len(pushes) == 3
    assert finished(world)["outcome"] == "merged"
    assert armed(world)


def test_a_pr_that_graphql_fails_once_opens_on_the_next_try(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    creates = flaky(monkeypatch, GitHub, "create_pr", [PR_GRAPHQL])

    world.run("run", str(BATCH))

    assert len(creates) == 2
    assert finished(world)["outcome"] == "merged"
    assert armed(world)


def test_announce_tries_its_label_and_its_comment_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    world.script("implement", ISSUE, {"output": BLOCKED})
    labels = flaky(monkeypatch, GitHub, "add_label", [LABEL_502], only=ISSUE)
    comments = flaky(monkeypatch, GitHub, "comment", [COMMENT_503], only=ISSUE)

    world.run("run", str(BATCH))

    assert (len(labels), len(comments)) == (2, 2)
    issue = world.gh()["issues"][str(ISSUE)]
    assert "blocked" in issue["labels"]
    assert len(issue["comments"]) == 1
    assert "Which one?" in issue["comments"][0]
    assert not [e for e in events(world) if e["event"] == "announce_failed"]


def test_a_rejected_push_isnt_tried_again(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    one_issue(world)
    pushes = flaky(monkeypatch, Git, "push", [PUSH_REJECTED])

    world.run("run", str(BATCH))

    assert len(pushes) == 1
    assert finished(world)["outcome"] == "failed"
    assert "rejected" in finished(world)["detail"]


def test_a_refused_pr_isnt_tried_again(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    one_issue(world)
    creates = flaky(monkeypatch, GitHub, "create_pr", [PR_REFUSED])

    world.run("run", str(BATCH))

    assert len(creates) == 1
    assert finished(world)["outcome"] == "failed"


def test_a_push_that_fails_every_try_fails_the_issue_after_3_tries(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    pushes = flaky(monkeypatch, Git, "push", [PUSH_500] * 3)

    world.run("run", str(BATCH))

    assert len(pushes) == 3
    end = finished(world)
    assert end["outcome"] == "failed"
    assert "Internal Server Error" in end["detail"]
    assert "failed after 3 tries" in end["detail"]
    assert "Internal Server Error" in world.gh()["issues"][str(ISSUE)]["comments"][0]
