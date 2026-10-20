"""An approved review's low findings get one fix pass before the PR (#252, integration tests)."""

from __future__ import annotations

from typing import Any

from batch_runs import APPROVED, BATCH, CHANGES, LIMIT_REACHED, calls_for, pr_for
from conftest import World
from review_rounds import finding

UNCLEAR_NAME = finding("low", "new", "a.py:2", "The name `x` says nothing.")
STALE_COMMENT = finding("low", "new", "b.py:5", "The comment describes the old loop.")


def approved(*findings: dict[str, str]) -> dict[str, Any]:
    return {"output": {"verdict": "approved", "findings": list(findings)}}


def prompt(call: dict[str, Any]) -> str:
    argv: list[str] = call["argv"]
    return argv[argv.index("-p") + 1]


def kinds(world: World) -> list[str]:
    return [call["kind"] for call in world.claude_calls()]


def test_an_approval_with_low_findings_sends_them_to_the_implementer_and_reviews_again(
    world: World,
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, approved(UNCLEAR_NAME), APPROVED)

    world.run("run", str(BATCH))

    assert kinds(world) == ["implement", "review", "fix", "review"]
    [fix] = calls_for(world, "fix", 10)
    assert fix["argv"][fix["argv"].index("--resume") + 1] == "session-implement-10-0"
    for text in (UNCLEAR_NAME["location"], UNCLEAR_NAME["problem"], UNCLEAR_NAME["suggestion"]):
        assert text in prompt(fix)
    pr = pr_for(world, 10)
    assert pr["armed"]
    assert UNCLEAR_NAME["problem"] not in pr["body"]


def test_the_low_pass_runs_once_and_the_next_reviews_lows_go_to_the_pr(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, approved(UNCLEAR_NAME), approved(STALE_COMMENT))

    world.run("run", str(BATCH))

    assert kinds(world) == ["implement", "review", "fix", "review"]
    body = pr_for(world, 10)["body"]
    assert "## Review findings" in body
    assert STALE_COMMENT["problem"] in body
    assert UNCLEAR_NAME["problem"] not in body


def test_a_rerun_doesnt_repeat_a_low_pass_that_ran_on_the_branch(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, approved(UNCLEAR_NAME), LIMIT_REACHED, approved(STALE_COMMENT))
    world.run("run", str(BATCH))
    assert kinds(world) == ["implement", "review", "fix", "review"]

    world.run("run", str(BATCH))

    assert len(calls_for(world, "fix", 10)) == 1
    body = pr_for(world, 10)["body"]
    assert STALE_COMMENT["problem"] in body


def test_the_low_pass_doesnt_count_as_a_round_that_asked_for_changes(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, approved(UNCLEAR_NAME), CHANGES, APPROVED)

    world.run("run", str(BATCH))

    assert kinds(world) == ["implement", "review", "fix", "review", "fix", "review"]
    assert "blocked" not in world.gh()["issues"]["10"]["labels"]
    assert pr_for(world, 10)["armed"]


def test_an_issue_still_blocks_after_review_rounds_that_asked_for_changes(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, approved(UNCLEAR_NAME), CHANGES, CHANGES)

    world.run("run", str(BATCH))

    assert kinds(world) == ["implement", "review", "fix", "review", "fix", "review"]
    issue = world.gh()["issues"]["10"]
    assert "blocked" in issue["labels"]
    assert "after 2 rounds" in issue["comments"][-1]
    assert world.gh()["prs"] == {}


def test_an_approval_without_findings_goes_to_the_pr_with_no_low_pass(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, APPROVED)

    world.run("run", str(BATCH))

    assert kinds(world) == ["implement", "review"]
    assert pr_for(world, 10)["armed"]
