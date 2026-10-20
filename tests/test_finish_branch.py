"""The cleanup after a merge deletes the merged branch before it fetches (#34, medium tests)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_batch.core.config import Config
from agent_batch.shell.git import Git
from agent_batch.shell.proc import CommandError
from clean_branches import local_branches
from conftest import World, git
from ship_branches import master_moves_on_the_remote

BRANCH = "10-issue-10"


def lane_on_a_merged_branch(world: World) -> tuple[Git, Path]:
    """A lane's worktree on an issue's branch, with a commit, as a merged issue leaves it."""
    runner = Git(Config())
    worktree = world.root / "lane-1"
    runner.add_lane_worktree(world.project, worktree)
    runner.start_branch(worktree, BRANCH)
    (worktree / "work.txt").write_text("work\n")
    git(worktree, "add", "-A")
    git(worktree, "commit", "--quiet", "-m", "feat: work")
    return runner, worktree


def test_a_failed_fetch_in_the_cleanup_leaves_no_merged_branch_behind(world: World) -> None:
    runner, worktree = lane_on_a_merged_branch(world)
    world.origin.rename(world.origin.with_name(f"{world.origin.name}.down"))

    with pytest.raises(CommandError, match="fetch"):
        runner.finish_branch(worktree, BRANCH)

    assert BRANCH not in local_branches(world)
    assert runner.current_branch(worktree) == ""


def test_a_successful_cleanup_detaches_at_the_latest_upstream_and_deletes_the_branch(
    world: World,
) -> None:
    runner, worktree = lane_on_a_merged_branch(world)
    latest = master_moves_on_the_remote(world)

    runner.finish_branch(worktree, BRANCH)

    assert BRANCH not in local_branches(world)
    assert runner.current_branch(worktree) == ""
    assert runner.head(worktree) == latest
