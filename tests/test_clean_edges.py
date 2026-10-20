"""`agent-batch clean` at its edges: what git won't let go, and a batch it can't clean (#111)."""

from __future__ import annotations

import pytest

from agent_batch import batch
from agent_batch.context import Context
from agent_batch.shell.proc import CommandError
from batch_runs import events
from clean_branches import MERGED, add_pr, branch_with_work, clean, local_branches, said_about
from conftest import World, git


def test_clean_keeps_a_merged_branch_checked_out_in_the_main_folder(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    head = branch_with_work(world, MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)
    git(world.project, "switch", "--quiet", MERGED)

    assert clean() == 0

    assert MERGED in local_branches(world)
    assert "main folder" in said_about(capsys.readouterr().out, MERGED)


def test_clean_never_deletes_the_base_branch(world: World) -> None:
    head = git(world.project, "rev-parse", "master").strip()
    add_pr(world, 90, "master", state="MERGED", head=head)
    git(world.project, "switch", "--quiet", "--detach")

    assert clean() == 0

    assert "master" in local_branches(world)


def test_clean_keeps_a_branch_whose_worktree_is_locked_and_says_why(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    head = branch_with_work(world, MERGED)
    worktree = world.root / "ship-51"
    git(world.project, "worktree", "add", "--quiet", "--lock", str(worktree), MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED in local_branches(world)
    assert worktree.is_dir()
    assert "the cleanup failed" in said_about(capsys.readouterr().out, MERGED)


def test_a_batch_goes_on_when_its_cleanup_fails(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fails(_ctx: Context) -> None:
        raise CommandError("`git worktree prune` failed: the disk is full")

    monkeypatch.setattr(batch, "clean_branches", fails)
    world.add_issue(10)
    world.add_batch(1, "Lane 1: #10\n")

    assert world.run("run", "1") == 0

    names = [event["event"] for event in events(world, 1)]
    assert "cleanup_failed" in names, names
    assert "merged" in names, names
