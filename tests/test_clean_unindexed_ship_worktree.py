"""`agent-batch clean` treats a ship worktree where Spotlight doesn't look as any other (#212).

run-batch makes its ship worktrees in `.agent-batch/worktrees.noindex/`, where the lanes' are on
macOS: one there isn't a lane's. Medium tests: real git, and a fake `gh`.
"""

from __future__ import annotations

import pytest

from clean_branches import MERGED, add_pr, branch_with_work, clean, local_branches, said_about
from conftest import World, git

FOLDERS = ["worktrees", "worktrees.noindex"]


@pytest.mark.parametrize("folder", FOLDERS)
def test_clean_deletes_a_merged_branch_and_its_ship_worktree_in_either_folder(
    world: World, capsys: pytest.CaptureFixture[str], folder: str
) -> None:
    head = branch_with_work(world, MERGED)
    ship = world.project / ".agent-batch" / folder / "ship-51"
    git(world.project, "worktree", "add", "--quiet", str(ship), MERGED)
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED not in local_branches(world)
    assert not ship.exists()
    assert "#83" in said_about(capsys.readouterr().out, MERGED)


@pytest.mark.parametrize("folder", FOLDERS)
def test_clean_keeps_a_merged_branch_whose_ship_worktree_has_changes_in_either_folder(
    world: World, capsys: pytest.CaptureFixture[str], folder: str
) -> None:
    head = branch_with_work(world, MERGED)
    ship = world.project / ".agent-batch" / folder / "ship-51"
    git(world.project, "worktree", "add", "--quiet", str(ship), MERGED)
    (ship / "unfinished.txt").write_text("a direct-mode fix\n")
    add_pr(world, 83, MERGED, state="MERGED", head=head)

    assert clean() == 0

    assert MERGED in local_branches(world)
    assert ship.is_dir()
    line = said_about(capsys.readouterr().out, MERGED)
    assert "ship-51 has changes" in line, line
    assert "the runner's" not in line, line
