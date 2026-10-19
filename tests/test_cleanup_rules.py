"""Which local branches the cleanup deletes, and what it says about the others (#111, small)."""

from __future__ import annotations

from pathlib import Path

from agent_batch.core.cleanup import decide
from agent_batch.core.model import LocalBranch, MergedPr

HEAD = "15bf722" + "0" * 33
OLDER = "89b4cd7" + "0" * 33


def test_a_branch_merged_at_its_head_goes() -> None:
    verdict = decide(LocalBranch("51-x", HEAD), [MergedPr(83, HEAD)], changed=False)

    assert verdict.delete
    assert verdict.pr == 83


def test_any_merged_pr_at_the_head_lets_a_reused_branch_name_go() -> None:
    merged = [MergedPr(70, OLDER), MergedPr(83, HEAD)]

    verdict = decide(LocalBranch("51-x", HEAD), merged, changed=False)

    assert verdict.delete
    assert verdict.pr == 83


def test_a_head_no_pr_merged_names_each_merged_prs_head() -> None:
    verdict = decide(LocalBranch("51-x", HEAD), [MergedPr(83, OLDER)], changed=False)

    assert not verdict.delete
    assert "15bf722" in verdict.reason
    assert "#83 merged at 89b4cd7" in verdict.reason


def test_a_branch_checked_out_in_the_main_folder_stays() -> None:
    branch = LocalBranch("51-x", HEAD, Path("/project"), main_folder=True)

    verdict = decide(branch, [MergedPr(83, HEAD)], changed=False)

    assert not verdict.delete
    assert "main folder" in verdict.reason


def test_a_worktree_with_changes_is_named_in_the_reason() -> None:
    branch = LocalBranch("51-x", HEAD, Path("/project/.agent-batch/worktrees/ship-51"))

    verdict = decide(branch, [MergedPr(83, HEAD)], changed=True)

    assert not verdict.delete
    assert "ship-51 has changes" in verdict.reason
