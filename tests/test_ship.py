"""`agent-batch ship`, the end of direct mode (medium tests)."""

from __future__ import annotations

from pathlib import Path

from conftest import World, git

CHANGES = {
    "output": {
        "verdict": "changes",
        "findings": [
            {
                "severity": "low",
                "origin": "new",
                "location": "a.py:3",
                "problem": "Unclear.",
                "suggestion": "Rename.",
            }
        ],
    }
}


def branch_with_work(world: World, branch: str, file: str = "feature.txt") -> Path:
    git(world.project, "switch", "--quiet", "--create", branch)
    path = world.project / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: work")
    body = world.root / "body.md"
    body.write_text("Adds the feature.\n")
    return body


def test_an_approved_branch_gets_its_pr_and_an_armed_merge(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    code = world.run("ship", "10", "--title", "feat: add the feature", "--body-file", str(body))

    assert code == 0
    pr = next(iter(world.gh()["prs"].values()))
    assert pr["title"] == "feat: add the feature"
    assert "Closes #10" in pr["body"]
    assert pr["armed"]


def test_a_high_risk_branch_waits_for_the_owner(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature", file="Makefile")

    assert world.run("ship", "10", "--title", "build: targets", "--body-file", str(body)) == 0

    pr = next(iter(world.gh()["prs"].values()))
    assert pr["armed"] is None
    assert pr["labels"] == ["risk:high"]


def test_review_findings_come_back_without_a_pr(world: World) -> None:
    world.add_issue(10)
    world.script("review", 10, CHANGES)
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "feat: x", "--body-file", str(body)) == 2
    assert world.gh()["prs"] == {}


def test_a_branch_not_named_after_the_issue_is_refused(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "something-else")

    assert world.run("ship", "10", "--title", "feat: x", "--body-file", str(body)) == 1
    assert world.claude_calls() == []


def test_an_issue_that_isnt_ready_is_refused(world: World) -> None:
    world.add_issue(10, labels=("task",))
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "feat: x", "--body-file", str(body)) == 1
