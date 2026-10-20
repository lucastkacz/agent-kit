"""`agent-batch clean` deletes the local branches whose PR merged, and only those (#111).

Medium tests: real git, and a fake `gh` that knows each PR's state and head.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clean_branches import (
    MERGED,
    OTHER,
    add_pr,
    branch_with_work,
    clean,
    local_branches,
    said_about,
)
from conftest import World, git


def worktrees(world: World) -> list[Path]:
    listed = git(world.project, "worktree", "list", "--porcelain").splitlines()
    return [Path(line.removeprefix("worktree ")) for line in listed if line.startswith("worktree ")]


def test_clean_deletes_a_branch_whose_pr_merged_at_its_head(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    head = branch_with_work(world, MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED not in local_branches(world)
    assert "master" in local_branches(world)
    assert "#83" in said_about(capsys.readouterr().out, MERGED)


def test_clean_removes_the_worktree_of_a_branch_whose_pr_merged(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    head = branch_with_work(world, MERGED)
    worktree = world.root / "ship-51"
    git(world.project, "worktree", "add", "--quiet", str(worktree), MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED not in local_branches(world)
    assert not worktree.exists()
    assert worktree.resolve() not in [path.resolve() for path in worktrees(world)]
    assert "#83" in said_about(capsys.readouterr().out, MERGED)


def test_clean_keeps_a_branch_with_no_merged_pr_and_says_why(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    open_head = branch_with_work(world, MERGED)
    branch_with_work(world, OTHER)
    add_pr(world, 83, MERGED, state="OPEN", head=open_head)

    assert clean() == 0

    assert {MERGED, OTHER} <= set(local_branches(world))
    out = capsys.readouterr().out
    for branch in (MERGED, OTHER):
        line = said_about(out, branch)
        assert "kept" in line, line
        assert "no merged pr" in line, line


def test_clean_keeps_a_branch_whose_head_differs_from_its_merged_prs_and_says_why(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    merged_head = branch_with_work(world, MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=merged_head)
    # Work that came after the merge, which GitHub doesn't have.
    git(world.project, "switch", "--quiet", MERGED)
    (world.project / "later.txt").write_text("later\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: later work")
    git(world.project, "switch", "--quiet", "master")

    assert clean() == 0

    assert MERGED in local_branches(world)
    line = said_about(capsys.readouterr().out, MERGED)
    assert "kept" in line, line
    assert "head" in line, line
    assert "#83" in line, line


@pytest.mark.parametrize("change", ["modified", "untracked"])
def test_clean_keeps_a_branch_whose_worktree_has_changes_and_says_why(
    world: World, capsys: pytest.CaptureFixture[str], change: str
) -> None:
    head = branch_with_work(world, MERGED)
    worktree = world.root / "ship-51"
    git(world.project, "worktree", "add", "--quiet", str(worktree), MERGED)
    if change == "modified":
        (worktree / f"{MERGED}.txt").write_text("changed, not committed\n")
    else:
        (worktree / "new.txt").write_text("not committed\n")
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED in local_branches(world)
    assert worktree.is_dir()
    line = said_about(capsys.readouterr().out, MERGED)
    assert "kept" in line, line
    assert "changes" in line, line
