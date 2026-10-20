"""`agent-batch clean` leaves a running lane alone, reads GitHub once, and deletes only the head
it checked (#111, medium tests)."""

from __future__ import annotations

import pytest

from agent_batch import clean as clean_module
from agent_batch.core.config import Config
from agent_batch.shell.git import Git
from agent_batch.shell.proc import CommandError
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


def gh_reads_of_one_branch(world: World) -> list[list[str]]:
    return [call for call in world.gh()["calls"] if call[:2] == ["pr", "list"] and "--head" in call]


def test_clean_keeps_a_merged_branch_a_lane_still_has_checked_out_and_says_why(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    head = branch_with_work(world, MERGED)
    lane = world.project / ".agent-batch" / "worktrees" / "lane-1"
    git(world.project, "worktree", "add", "--quiet", str(lane), MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED in local_branches(world)
    assert lane.is_dir()
    line = said_about(capsys.readouterr().out, MERGED)
    assert "kept" in line, line
    assert "lane-1 worktree" in line, line


def test_clean_reads_the_merged_prs_once_when_they_all_fit(world: World) -> None:
    for number, branch in ((83, MERGED), (99, OTHER)):
        add_pr(world, number, branch, state="MERGED", head=branch_with_work(world, branch))

    assert clean() == 0

    assert not {MERGED, OTHER} & set(local_branches(world))
    assert gh_reads_of_one_branch(world) == []


def test_clean_asks_about_a_branch_alone_when_the_latest_merged_prs_fill_the_read(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(clean_module, "RECENT_MERGED", 1)
    for number, branch in ((83, MERGED), (99, OTHER)):
        add_pr(world, number, branch, state="MERGED", head=branch_with_work(world, branch))

    assert clean() == 0

    assert not {MERGED, OTHER} & set(local_branches(world))
    assert len(gh_reads_of_one_branch(world)) == 1


def test_deleting_a_branch_refuses_when_it_moved_since_it_was_checked(world: World) -> None:
    checked = branch_with_work(world, MERGED)
    git(world.project, "switch", "--quiet", MERGED)
    (world.project / "later.txt").write_text("later\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: later work")
    git(world.project, "switch", "--quiet", "master")
    moved = git(world.project, "rev-parse", MERGED).strip()

    with pytest.raises(CommandError, match="update-ref"):
        Git(Config()).delete_branch(world.project, MERGED, checked)

    assert git(world.project, "rev-parse", MERGED).strip() == moved
