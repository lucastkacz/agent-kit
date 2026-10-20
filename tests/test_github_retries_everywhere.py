"""A GitHub server error on the runner's other calls is tried again, as #195's are (#210).

`edit_pr`, `pr_state`, `arm_merge`, `hold`'s risk label and comment, and the follow-up issue's
creation. The tests run `agent-batch run` with real git and fake `gh` and `claude` (medium tests).
"""

from __future__ import annotations

from typing import Any

import pytest

from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from batch_runs import BATCH, HIGH_RISK_WORK, add_open_pr, done, events, pr_for
from conftest import World
from github_server_errors import ISSUE, finished, flaky, one_issue

EDIT_502 = "`gh pr edit` failed: HTTP 502: Bad Gateway (https://api.github.com/graphql)"
VIEW_GRAPHQL = (
    "`gh pr view` failed: GraphQL: Something went wrong while executing your query. This may "
    "be the result of a timeout, or it could be a GitHub bug."
)
MERGE_503 = "`gh pr merge` failed: HTTP 503: Service Unavailable (https://api.github.com/graphql)"
PR_LABEL_502 = "`gh pr edit` failed: HTTP 502: Bad Gateway (https://api.github.com/graphql)"
COMMENT_502 = "`gh pr comment` failed: HTTP 502: Bad Gateway (https://api.github.com/graphql)"
CREATE_500 = (
    "`gh issue create` failed: HTTP 500: Internal Server Error (https://api.github.com/graphql)"
)
DATES = {"kind": "idea", "title": "Dates drift", "body": "Seen in the importer."}
CONFLICT = {"file": "shared.txt", "content": "another lane\n"}
HIGH_RISK_COMMENT = "**High risk: the owner merges this PR.**"


def saved_then_failed(
    monkeypatch: pytest.MonkeyPatch, name: str, error: str
) -> list[tuple[Any, ...]]:
    """Makes the first call to `GitHub.name` do its work and then fail, as a GraphQL timeout can."""
    original = getattr(GitHub, name)
    calls: list[tuple[Any, ...]] = []

    def call(self: GitHub, *args: Any) -> Any:
        calls.append(args)
        result = original(self, *args)
        if len(calls) == 1:
            raise CommandError(error)
        return result

    monkeypatch.setattr(GitHub, name, call)
    return calls


def follow_ups(world: World) -> list[dict[str, Any]]:
    return [i for n, i in world.gh()["issues"].items() if n not in (str(BATCH), str(ISSUE))]


def merged_and_armed(world: World) -> None:
    assert finished(world)["outcome"] == "merged", finished(world)["detail"]
    assert pr_for(world, ISSUE)["armed"], "the PR's merge wasn't armed"


def test_publish_edits_an_existing_pr_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    add_open_pr(world, 50, f"{ISSUE}-issue-{ISSUE}")
    edits = flaky(monkeypatch, GitHub, "edit_pr", [EDIT_502])

    world.run("run", str(BATCH))

    assert len(edits) == 2
    merged_and_armed(world)
    assert pr_for(world, ISSUE)["title"] == f"feat: deliver #{ISSUE}"


def test_the_pr_edit_after_a_resolved_conflict_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    world.script("implement", ISSUE, {**done(), "files": ["shared.txt"]})
    world.pr_views(
        f"{ISSUE}-issue-{ISSUE}",
        {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": CONFLICT},
    )
    edits = flaky(monkeypatch, GitHub, "edit_pr", [EDIT_502])

    world.run("run", str(BATCH))

    assert len(edits) == 2
    merged_and_armed(world)


def test_a_pr_state_read_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    reads = flaky(monkeypatch, GitHub, "pr_state", [VIEW_GRAPHQL])

    world.run("run", str(BATCH))

    assert len(reads) >= 2
    merged_and_armed(world)


def test_arming_the_merge_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_issue(world)
    arms = flaky(monkeypatch, GitHub, "arm_merge", [MERGE_503])

    world.run("run", str(BATCH))

    assert len(arms) == 2
    merged_and_armed(world)


def high_risk_issue(world: World) -> None:
    one_issue(world)
    world.script("implement", ISSUE, HIGH_RISK_WORK)


def held(world: World) -> None:
    assert finished(world)["outcome"] == "waiting for the owner", finished(world)["detail"]
    pr = pr_for(world, ISSUE)
    assert pr["labels"] == ["risk:high"]
    assert len(pr["comments"]) == 1, pr["comments"]
    assert HIGH_RISK_COMMENT in pr["comments"][0]


def test_the_risk_label_of_a_held_pr_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    high_risk_issue(world)
    labels = flaky(monkeypatch, GitHub, "pr_add_label", [PR_LABEL_502])

    world.run("run", str(BATCH))

    assert len(labels) == 2
    held(world)


def test_the_comment_of_a_held_pr_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    high_risk_issue(world)
    comments = flaky(monkeypatch, GitHub, "pr_comment", [COMMENT_502])

    world.run("run", str(BATCH))

    assert len(comments) == 2
    held(world)


def test_a_held_prs_comment_that_github_saved_before_its_server_error_isnt_posted_twice(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    high_risk_issue(world)
    saved_then_failed(monkeypatch, "pr_comment", COMMENT_502)

    world.run("run", str(BATCH))

    held(world)


def run_with_found_work(world: World) -> None:
    one_issue(world)
    world.script("implement", ISSUE, done(found=[DATES]))
    world.run("run", str(BATCH))


def filed_once(world: World) -> None:
    merged_and_armed(world)
    [issue] = follow_ups(world)
    assert issue["title"] == DATES["title"]
    [event] = [e for e in events(world, BATCH) if e["event"] == "issue_found"]
    assert event["found"] == issue["number"]


def test_the_follow_up_issues_creation_is_tried_again_after_a_server_error(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    creates = flaky(monkeypatch, GitHub, "create_issue", [CREATE_500])

    run_with_found_work(world)

    assert len(creates) == 2
    filed_once(world)


def test_a_follow_up_issue_github_created_before_its_server_error_isnt_created_twice(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved_then_failed(monkeypatch, "create_issue", CREATE_500)

    run_with_found_work(world)

    filed_once(world)
