"""A summary line points to the event log when the issue got no comment (#54's review).

The unit test is small; the others run `agent-batch run` with real git and fake `gh` and `claude`
(medium tests).
"""

from __future__ import annotations

import pytest

from agent_batch.core import report
from agent_batch.core.model import IssueReport, Outcome
from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from conftest import World

BATCH = 1
TO_THE_LOG = "; see the batch's event log (`events.jsonl`)."


def _summary(world: World) -> str:
    comments: list[str] = world.gh()["issues"][str(BATCH)]["comments"]
    return comments[-1]


def _needs(summary: str, number: int) -> str:
    return next(line for line in summary.splitlines() if line.startswith(f"- #{number}: "))


def test_a_multi_line_detail_with_no_comment_points_to_the_event_log() -> None:
    reports = [IssueReport(13, Outcome.FAILED, "It broke:\nfatal: no network", unannounced=True)]

    assert report.render(reports, 60).endswith(f"- #13: failed. It broke{TO_THE_LOG}\n")


def test_a_lane_whose_worktree_fails_points_its_issues_to_their_comment(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    # Without its remote, git's fetch fails with several lines of explanation.
    world.origin.rename(world.origin.with_name(f"{world.origin.name}.down"))

    world.run("run", str(BATCH))

    line = _needs(_summary(world), 10)
    assert line.startswith("- #10: failed. the lane's worktree failed: "), line
    # Since #127 the runner comments on these issues too.
    assert line.endswith("; see #10's comment."), line


def test_an_issue_whose_comment_fails_points_to_the_event_log(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    question = "Which currency should the export use?\n\nA) USD. B) ARS. I recommend A."
    blocked = {"status": "blocked", "title": "", "pr_body": "", "message": question, "found": []}
    world.script("implement", 10, {"output": blocked})
    comment = GitHub.comment

    def comment_but_on_10(gh: GitHub, number: int, body: str) -> None:
        if number == 10:
            raise CommandError("`gh issue comment` failed: error connecting to api.github.com")
        comment(gh, number, body)

    monkeypatch.setattr(GitHub, "comment", comment_but_on_10)

    world.run("run", str(BATCH))

    line = _needs(_summary(world), 10)
    assert line == (
        "- #10: blocked. Which currency should the export use? "
        "See the batch's event log (`events.jsonl`)."
    )
