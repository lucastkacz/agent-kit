"""`agent-batch run` end to end, with real git and fake `gh` and `claude` (medium tests)."""

from __future__ import annotations

import json
from typing import Any

from batch_runs import APPROVED, BATCH, CHANGES, done, pr_for
from conftest import World


def events(world: World) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_a_lane_merges_its_issues_in_order_and_keeps_the_implementer_session(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_issue(12)
    world.add_batch(BATCH, "Lane 1: #10, #11\nLane 2: #12\n")

    assert world.run("run", str(BATCH)) == 0

    for issue in (10, 11, 12):
        pr = pr_for(world, issue)
        assert pr["armed"], f"#{issue}'s merge wasn't armed"
        assert f"Closes #{issue}" in pr["body"]
        assert pr["title"] == f"feat: deliver #{issue}"
    implement_11 = next(
        c for c in world.claude_calls() if c["kind"] == "implement" and c["number"] == 11
    )
    assert (
        implement_11["argv"][implement_11["argv"].index("--resume") + 1] == "session-implement-10-0"
    )
    summary = world.gh()["issues"][str(BATCH)]["comments"][-1]
    assert "## Batch summary" in summary
    assert "merged 3" in summary
    assert "**Human checks:** 3" in summary


def test_claude_runs_without_api_keys_or_session_markers_and_without_prompts(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")

    world.run("run", str(BATCH))

    calls = world.claude_calls()
    assert {call["kind"] for call in calls} == {"implement", "review"}
    for call in calls:
        assert not call["api_key"]
        assert not call["auth_token"]
        assert not call["claudecode"]
        assert call["argv"][call["argv"].index("--permission-prompts") + 1] == "none"
    review = next(call for call in calls if call["kind"] == "review")
    assert review["argv"][review["argv"].index("--permission-mode") + 1] == "dontAsk"
    assert "Bash(git push *)" in review["argv"]


def test_a_blocked_issue_gets_its_question_and_defers_the_rest_of_its_lane(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_issue(12)
    world.add_batch(BATCH, "Lane 1: #10, #11\nLane 2: #12\n")
    question = "Should the export include archived cards?"
    world.script(
        "implement", 10, {"output": {**done()["output"], "status": "blocked", "message": question}}
    )

    world.run("run", str(BATCH))

    issues = world.gh()["issues"]
    assert "blocked" in issues["10"]["labels"]
    assert question in issues["10"]["comments"][-1]
    assert not any(c["number"] == 11 for c in world.claude_calls()), "#11 should have waited"
    assert pr_for(world, 12)["armed"]
    assert "deferred 1" in issues[str(BATCH)]["comments"][-1]


def test_two_review_rounds_without_approval_block_the_issue(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, CHANGES, CHANGES)

    world.run("run", str(BATCH))

    kinds = [call["kind"] for call in world.claude_calls()]
    assert kinds == ["implement", "review", "fix", "review"]
    issue = world.gh()["issues"]["10"]
    assert "blocked" in issue["labels"]
    assert "after 2 rounds" in issue["comments"][-1]
    assert world.gh()["prs"] == {}


def test_a_review_finding_goes_back_to_the_implementer_and_then_merges(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, CHANGES, APPROVED)

    world.run("run", str(BATCH))

    fix = next(call for call in world.claude_calls() if call["kind"] == "fix")
    assert fix["argv"][fix["argv"].index("--resume") + 1] == "session-implement-10-0"
    assert pr_for(world, 10)["armed"]


def test_a_high_risk_change_waits_for_the_owner_with_its_reasons(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    world.script("implement", 10, {**done(), "files": [".github/workflows/ci.yml"]})

    world.run("run", str(BATCH))

    pr = pr_for(world, 10)
    assert pr["armed"] is None
    assert pr["labels"] == ["risk:high"]
    assert "`.github/workflows/ci.yml` matches `.github/`" in pr["comments"][-1]
    assert not any(call["number"] == 11 for call in world.claude_calls())


def test_the_budget_stops_new_issues_from_starting(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\nBudget: 1 issue\n")

    world.run("run", str(BATCH))

    assert {call["number"] for call in world.claude_calls()} == {10}
    assert "deferred 1" in world.gh()["issues"][str(BATCH)]["comments"][-1]


def test_the_budget_flags_stop_new_issues_from_starting(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")

    assert world.run("run", "--max-issues", "1", "--max-hours", "2.5", str(BATCH)) == 0

    assert {call["number"] for call in world.claude_calls()} == {10}
    assert "deferred 1" in world.gh()["issues"][str(BATCH)]["comments"][-1]


def test_issues_not_opened_by_the_owner_are_skipped_without_a_word(world: World) -> None:
    world.add_issue(10, author="stranger")
    world.add_batch(BATCH, "Lane 1: #10\n")

    world.run("run", str(BATCH))

    assert world.claude_calls() == []
    assert world.gh()["issues"]["10"]["comments"] == []
    assert "skipped 1" in world.gh()["issues"][str(BATCH)]["comments"][-1]


def test_the_usage_limit_stops_the_batch_and_leaves_the_issue_ready(world: World) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10\nLane 2: #11\n")
    world.script("implement", 10, {"error": "Claude usage limit reached."})

    world.run("run", "--lanes", "1", str(BATCH))

    issue = world.gh()["issues"]["10"]
    assert "blocked" not in issue["labels"]
    assert issue["comments"] == []
    assert not any(call["number"] == 11 for call in world.claude_calls())
    assert "interrupted 1" in world.gh()["issues"][str(BATCH)]["comments"][-1]


def test_a_conflict_with_master_is_resolved_reviewed_again_and_merged(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {**done(), "files": ["shared.txt"]})
    conflict = {"file": "shared.txt", "content": "another lane\n"}
    world.pr_views(
        "10-issue-10",
        {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": conflict},
    )

    world.run("run", str(BATCH))

    kinds = [call["kind"] for call in world.claude_calls()]
    assert kinds == ["implement", "review", "resolve", "review"]
    merges = [call for call in world.gh()["calls"] if call[:2] == ["pr", "merge"]]
    assert len(merges) == 2
    assert merges[0][-1] != merges[1][-1], "the second merge must be pinned to the new commit"


def test_found_work_becomes_issues_without_ready(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    found = [{"kind": "bug", "title": "Dates drift", "body": "Seen in the importer."}]
    world.script("implement", 10, done(found=found))

    world.run("run", str(BATCH))

    created = [i for i in world.gh()["issues"].values() if i["title"] == "Dates drift"]
    assert len(created) == 1
    assert created[0]["labels"] == ["bug"]
    assert "Found while working on #10." in created[0]["body"]


def test_a_failed_check_blocks_the_issue(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    failed = {"state": "OPEN", "mergeable": "MERGEABLE", "checks": [{"conclusion": "FAILURE"}]}
    world.pr_views("10-issue-10", failed)

    world.run("run", str(BATCH))

    issue = world.gh()["issues"]["10"]
    assert "blocked" in issue["labels"]
    assert "checks failed" in issue["comments"][-1]


# The PR merges, then the connection drops before the cleanup's fetch (batch #21, issue #19).
MERGED_THEN_OFFLINE = {"state": "MERGED", "mergeable": "MERGEABLE", "remote_down": True}


def test_a_merged_issue_stays_merged_and_untouched_when_the_cleanup_fails(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.pr_views("10-issue-10", MERGED_THEN_OFFLINE)

    world.run("run", str(BATCH))

    finished = [event for event in events(world) if event["event"] == "issue_finished"]
    assert [event["outcome"] for event in finished] == ["merged"]
    issue = world.gh()["issues"]["10"]
    assert issue["labels"] == ["task", "ready"]
    assert issue["comments"] == []
    assert "merged 1" in world.gh()["issues"][str(BATCH)]["comments"][-1]


def test_a_failed_cleanup_after_the_merge_is_logged_with_the_command_error(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.pr_views("10-issue-10", MERGED_THEN_OFFLINE)

    world.run("run", str(BATCH))

    failed = [event for event in events(world) if event["event"] == "cleanup_failed"]
    assert [event.get("issue") for event in failed] == [10]
    assert "`git fetch --quiet` failed" in failed[0]["detail"]
    assert "does not appear to be a git repository" in failed[0]["detail"]


def test_a_batch_without_a_lane_plan_is_refused(world: World) -> None:
    world.add_batch(BATCH, "No plan here.\n")

    assert world.run("run", str(BATCH)) == 1
    assert world.claude_calls() == []


def test_a_batch_opened_by_someone_else_is_refused(world: World) -> None:
    world.add_batch(BATCH, "Lane 1: #10\n", author="stranger")

    assert world.run("run", str(BATCH)) == 1
