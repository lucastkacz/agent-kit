"""`agent-batch clean` deletes the local branches whose PR merged, and only those (#111).

Medium tests: real git, and a fake `gh` that knows each PR's state and head.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_batch import cli
from conftest import World, git

MERGED = "51-a-resumed-run-that-s-replaced-loses-its"
OTHER = "66-re-running-a-batch-skips-a-merged-issue"


def clean() -> int:
    """`agent-batch clean`'s exit code, also when argparse exits on a usage error."""
    try:
        return cli.main(["clean"])
    except SystemExit as exited:
        return int(exited.code or 0)


def branch_with_work(world: World, name: str) -> str:
    """A local branch one commit ahead of master, as a lane leaves it; returns its head."""
    git(world.project, "switch", "--quiet", "--create", name)
    (world.project / f"{name}.txt").write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", f"feat: {name}")
    git(world.project, "switch", "--quiet", "master")
    return git(world.project, "rev-parse", name).strip()


def add_pr(world: World, number: int, branch: str, *, state: str, head: str) -> None:
    """A PR on the branch, in the given state, whose head on GitHub is `head`."""
    gh = world.gh()
    gh["prs"][str(number)] = {
        "number": number,
        "branch": branch,
        "base": "master",
        "title": "feat: a thing",
        "body": "Closes #10",
        "state": state,
        "labels": [],
        "comments": [],
        "armed": None,
        "views": [],
        "head": head,
    }
    world.gh_state.write_text(json.dumps(gh))


def local_branches(world: World) -> list[str]:
    return git(world.project, "branch", "--format=%(refname:short)").split()


def worktrees(world: World) -> list[Path]:
    listed = git(world.project, "worktree", "list", "--porcelain").splitlines()
    return [Path(line.removeprefix("worktree ")) for line in listed if line.startswith("worktree ")]


def said_about(out: str, branch: str) -> str:
    """The line of clean's output about the branch."""
    lines = [line for line in out.splitlines() if branch in line]
    assert len(lines) == 1, out
    return lines[0].lower()


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
