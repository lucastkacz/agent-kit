"""run-batch's ship and trial worktrees go where Spotlight doesn't index them (#212).

Each of them runs `make setup`, which builds a fresh `.venv`, and Spotlight skips a folder whose
name ends in `.noindex`, as the lanes' worktrees already do on macOS (#198).
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "plugin" / "skills"
RUN_BATCH = SKILLS / "run-batch" / "SKILL.md"
PLAN_BATCH = SKILLS / "plan-batch" / "SKILL.md"
# A ship or trial worktree's path, such as `.agent-batch/worktrees/ship-<n>`, and not the ship's
# log folder, `.agent-batch/ship-<n>/`.
WORKTREE = re.compile(r"\.agent-batch/([^/\s`]+)/(ship-<n>|trial-<batch>)")


def _folders(text: str) -> set[str]:
    return {folder for folder, _ in WORKTREE.findall(text)}


def _folder() -> str:
    """The one folder run-batch names for its ship and trial worktrees."""
    text = RUN_BATCH.read_text(encoding="utf-8")
    kinds = {kind for _, kind in WORKTREE.findall(text)}
    assert kinds == {"ship-<n>", "trial-<batch>"}, kinds
    folders = _folders(text)
    assert len(folders) == 1, f"run-batch names its worktrees in several folders: {folders}"
    [folder] = folders
    return folder


def test_run_batch_makes_its_ship_and_trial_worktrees_in_a_folder_spotlight_skips() -> None:
    folder = _folder()

    assert folder.endswith(".noindex"), f"Spotlight indexes .agent-batch/{folder}"


def test_every_step_that_makes_reuses_or_removes_a_ship_worktree_names_that_folder() -> None:
    ship = f".agent-batch/{_folder()}/ship-<n>"
    text = RUN_BATCH.read_text(encoding="utf-8")

    for step in (
        f"git worktree add {ship} -b <branch> origin/<branch>",
        f"git worktree add {ship} <branch>",
        f"git worktree remove {ship}",
        f"its kept `{ship}` is at `origin/<branch>`",
        f"one at a time, in `{ship}`",
    ):
        assert step in text, step


def test_every_step_that_makes_or_removes_the_trial_worktree_names_that_folder() -> None:
    trial = f".agent-batch/{_folder()}/trial-<batch>"
    text = RUN_BATCH.read_text(encoding="utf-8")

    assert f"If `{trial}` is left from an interrupted session" in text, text
    assert f"git worktree add --detach {trial} origin/master" in text, text
    assert text.count(f"git worktree remove --force {trial}") == 2, text


def test_plan_batch_names_the_kept_ship_worktree_in_that_same_folder() -> None:
    text = PLAN_BATCH.read_text(encoding="utf-8")

    assert _folders(text) == {_folder()}, _folders(text)
    assert f"run-batch keeps its `.agent-batch/{_folder()}/ship-<n>`" in text, text
