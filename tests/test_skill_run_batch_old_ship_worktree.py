"""A ship worktree kept in the old folder moves to the new one before it's reused (#212).

A worktree kept before the ship worktrees moved to `worktrees.noindex/` holds its branch, so a
new `git worktree add` of that branch would fail.
"""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "run-batch" / "SKILL.md"


def test_a_ship_worktree_left_in_the_old_folder_is_moved_before_it_is_reused() -> None:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("2. `git worktree add .agent-batch/worktrees.noindex/ship-<n>")
    step = text[start : text.index("\n3. ", start)]

    moved = step.index("git worktree move")
    assert "`.agent-batch/worktrees/`" in step[:moved], step
    assert "`.agent-batch/worktrees.noindex/ship-<n>`" in step[moved:], step
    assert moved < step.index("reuse it"), step


def test_a_resume_finds_a_kept_ship_worktree_left_in_the_old_folder() -> None:
    text = SKILL.read_text(encoding="utf-8")
    kept = text[text.index("a routine whose run ended") :]
    kept = kept[: kept.index("\n")]

    assert "moved there first as in that section's step 2" in kept, kept
