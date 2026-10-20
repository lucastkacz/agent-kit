"""After a low pass, a lane's run can reach a branch's third review, where a new medium finding is
filed instead of blocking (#252, SPEC §5)."""

from __future__ import annotations

from batch_runs import BATCH, CHANGES, pr_for
from conftest import World
from review_rounds import SLOW, changes, finding

UNCLEAR_NAME = finding("low", "new", "a.py:2", "The name `x` says nothing.")
APPROVED_WITH_A_LOW = {"output": {"verdict": "approved", "findings": [UNCLEAR_NAME]}}


def test_the_third_review_after_a_low_pass_files_a_new_medium_finding(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("review", 10, APPROVED_WITH_A_LOW, CHANGES, changes(SLOW))

    world.run("run", str(BATCH))

    kinds = [call["kind"] for call in world.claude_calls()]
    assert kinds == ["implement", "review", "fix", "review", "fix", "review"]
    assert pr_for(world, 10)["armed"]
    [follow_up] = [
        issue for number, issue in world.gh()["issues"].items() if number not in ("10", str(BATCH))
    ]
    assert SLOW["problem"] in follow_up["title"] + follow_up["body"]
    assert "blocked" not in world.gh()["issues"]["10"]["labels"]
