"""A batch started before the lanes moved to `worktrees.noindex` still resumes and cleans up (#198).

They run `agent-batch` with real git and fake `gh` and `claude` (medium tests).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_runs import pr_for
from clean_branches import MERGED, add_pr, branch_with_work, clean, local_branches, said_about
from conftest import World, git

BATCH = 1
BRANCH = "10-issue-10"


def _state(world: World) -> Path:
    return world.project / ".agent-batch"


def test_a_resumed_batch_works_on_in_the_new_folder_a_branch_the_old_lane_holds(
    world: World,
) -> None:
    old = _state(world) / "worktrees" / "lane-1"
    git(world.project, "worktree", "add", "--quiet", "-b", BRANCH, str(old), "origin/master")
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")

    assert world.run("run", str(BATCH)) == 0

    assert not old.exists(), "the old lane's worktree stayed"
    new = (_state(world) / "worktrees.noindex" / "lane-1").resolve()
    assert {Path(call["cwd"]).resolve() for call in world.claude_calls()} == {new}
    assert pr_for(world, 10)["branch"] == BRANCH


def test_clean_keeps_a_merged_branch_a_lane_in_the_new_folder_has_checked_out(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    head = branch_with_work(world, MERGED)
    lane = _state(world) / "worktrees.noindex" / "lane-1"
    git(world.project, "worktree", "add", "--quiet", str(lane), MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED in local_branches(world)
    assert "lane-1 worktree" in said_about(capsys.readouterr().out, MERGED)
