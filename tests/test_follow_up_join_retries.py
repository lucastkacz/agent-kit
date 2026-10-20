"""A server error while found work joins an open follow-up issue is tried again (#232).

The issue's read, the comment and the relabel. The tests run `agent-batch run` with real git and
fake `gh` and `claude` (medium tests), and read SPEC §5 (small tests).
"""

from __future__ import annotations

from typing import Any

import pytest

from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from batch_runs import APPROVED, BATCH, CHANGES, done, pr_for
from conftest import World
from follow_ups import CONFLICTING, DATES, follow_ups, issue_found
from github_server_errors import ISSUE, finished, one_issue
from review_rounds import SLOW, changes
from spec_text import SPEC, flat

CACHE = {"kind": "task", "title": "Cache the parse", "body": "It parses each file twice."}
VIEW_502 = "`gh issue view` failed: HTTP 502: Bad Gateway (https://api.github.com/graphql)"
COMMENT_500 = (
    "`gh issue comment` failed: HTTP 500: Internal Server Error (https://api.github.com/graphql)"
)
EDIT_GRAPHQL = (
    "`gh issue edit` failed: GraphQL: Something went wrong while executing your query. This may "
    "be the result of a timeout, or it could be a GitHub bug."
)


def on_the_follow_up(
    monkeypatch: pytest.MonkeyPatch, name: str, errors: list[str], *, saved: bool = False
) -> list[tuple[Any, ...]]:
    """Makes `GitHub.name` fail on the follow-up issue with each of `errors`, then work.

    With `saved`, each failing call does its work before it fails, as a GraphQL timeout can.
    Calls on the issue worked on and on its batch go through untouched.
    """
    original = getattr(GitHub, name)
    calls: list[tuple[Any, ...]] = []
    left = list(errors)

    def call(self: GitHub, number: int, *args: Any) -> Any:
        if number in (ISSUE, BATCH):
            return original(self, number, *args)
        calls.append((number, *args))
        if not left:
            return original(self, number, *args)
        if saved:
            original(self, number, *args)
        raise CommandError(left.pop(0))

    monkeypatch.setattr(GitHub, name, call)
    return calls


def run_where_a_finding_joins_the_follow_up(world: World) -> None:
    """The fix's found work opens a `task` follow-up; the third review's `bug` joins it."""
    one_issue(world)
    world.script("implement", ISSUE, {**done(), "files": ["shared.txt"]})
    world.script("fix", ISSUE, done(found=[DATES, CACHE]))
    world.script("review", ISSUE, CHANGES, APPROVED, changes(SLOW))
    world.pr_views(f"{ISSUE}-issue-{ISSUE}", CONFLICTING)
    world.run("run", str(BATCH))


def joined_once(world: World) -> None:
    assert finished(world)["outcome"] == "merged", finished(world)["detail"]
    assert pr_for(world, ISSUE)["armed"], "the PR's merge wasn't armed"
    [issue] = follow_ups(world)
    joined = [comment for comment in issue["comments"] if SLOW["problem"] in comment]
    assert len(joined) == 1, issue["comments"]
    assert issue["labels"] == ["bug"]
    assert len(issue_found(world)) == 1


@pytest.mark.parametrize(
    ("name", "error"),
    [("issue", VIEW_502), ("comment", COMMENT_500), ("relabel", EDIT_GRAPHQL)],
    ids=["read", "comment", "relabel"],
)
def test_a_call_on_the_open_follow_up_issue_is_tried_up_to_3_times_after_server_errors(
    world: World, monkeypatch: pytest.MonkeyPatch, name: str, error: str
) -> None:
    calls = on_the_follow_up(monkeypatch, name, [error, error])

    run_where_a_finding_joins_the_follow_up(world)

    assert len(calls) == 3, calls
    joined_once(world)


def test_a_comment_github_saved_before_its_server_error_isnt_posted_twice_on_the_follow_up(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    on_the_follow_up(monkeypatch, "comment", [COMMENT_500], saved=True)

    run_where_a_finding_joins_the_follow_up(world)

    joined_once(world)


def test_spec_5_step_6_lists_the_open_follow_up_issues_read_comment_and_relabel() -> None:
    step = flat(SPEC.read_text(encoding="utf-8"), "6. **Pull request.**", "\n7. ")
    for token in (
        "the open follow-up issue's read, comment and relabel",
        "the follow-up issue or its comment again",
    ):
        assert token in step, (token, step)
