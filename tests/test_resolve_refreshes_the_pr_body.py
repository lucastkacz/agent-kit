"""After a conflict, the PR body gets the findings of the review that approved it (#75, medium)."""

from __future__ import annotations

from conftest import World
from test_batch import BATCH, done, pr_for


def approved(problem: str) -> dict[str, object]:
    finding = {
        "severity": "low",
        "origin": "new",
        "location": "a.py:1",
        "problem": problem,
        "suggestion": "Tidy.",
    }
    return {"output": {"verdict": "approved", "findings": [finding]}}


def test_the_review_after_a_conflict_puts_its_findings_in_the_pr_body(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {**done(), "files": ["shared.txt"]})
    world.script("review", 10, approved("Before the merge."), approved("After the merge."))
    conflict = {"file": "shared.txt", "content": "another lane\n"}
    world.pr_views(
        "10-issue-10",
        {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": conflict},
    )

    world.run("run", str(BATCH))

    body = pr_for(world, 10)["body"]
    assert "After the merge." in body
    assert "Before the merge." not in body
