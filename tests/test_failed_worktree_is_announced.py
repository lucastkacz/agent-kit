"""A lane whose worktree fails announces its issues, and a question ends its own line (#127).

The integration test runs `agent-batch run` with real git and fake `gh` and `claude` (medium);
the others are small.
"""

from __future__ import annotations

import pytest

from agent_batch.core import report
from agent_batch.core.config import BLOCKED
from agent_batch.core.model import IssueReport, Outcome
from batch_runs import BATCH
from conftest import World


def test_a_lane_whose_worktree_fails_labels_and_comments_each_of_its_issues(
    world: World,
) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    # Without its remote, git's fetch fails, and with it the lane's worktree.
    world.origin.rename(world.origin.with_name(f"{world.origin.name}.down"))

    world.run("run", str(BATCH))

    issues = world.gh()["issues"]
    for number in ("10", "11"):
        assert BLOCKED in issues[number]["labels"], number
        comments: list[str] = issues[number]["comments"]
        assert len(comments) == 1, comments
        assert "**The batch couldn't finish this issue.**" in comments[0]
        assert "the lane's worktree failed: " in comments[0]
        assert "fetch" in comments[0]


def _needs(detail: str) -> str:
    text = report.render([IssueReport(13, Outcome.BLOCKED, detail)], 60)
    return text.splitlines()[-1]


@pytest.mark.parametrize("detail", ["Which currency?", "It broke again!"])
def test_a_one_line_detail_that_ends_a_question_or_an_exclamation_gets_no_period(
    detail: str,
) -> None:
    assert _needs(detail) == f"- #13: blocked. {detail}"


def test_a_one_line_detail_that_ends_otherwise_still_gets_a_period() -> None:
    assert _needs("The PR conflicts with master") == (
        "- #13: blocked. The PR conflicts with master."
    )
