"""The test modules #225 named use the helper modules' helpers, not copies of their own (#239)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
HELPERS = ("batch_runs", "clean_branches")
# A module that used `BATCH = 1` keeps `BATCH` and `APPROVED` from `batch_runs`.
BATCH_ONE = (
    "test_denials.py",
    "test_failed_worktree_is_announced.py",
    "test_keep_awake_any_computer.py",
    "test_keep_awake.py",
    "test_live_progress.py",
    "test_lighter_batches.py",
    "test_lighter_batches_resume.py",
    "test_live_progress_conflict.py",
    "test_model_line.py",
    "test_needs_owner_without_a_comment.py",
    "test_power.py",
    "test_replaced_resumed_run.py",
    "test_resumed_batch_cost_estimate.py",
    "test_review_cost_and_time.py",
    "test_running_cost_estimate.py",
    "test_sleep.py",
    "test_start_comment_lanes.py",
)
COPIES = [
    *((module, "BATCH") for module in BATCH_ONE),
    *((module, "APPROVED") for module in BATCH_ONE),
    ("test_batch.py", "events"),
    ("test_lane_hook_denials.py", "summary"),
    ("test_clean_when_batches_start_and_close.py", "local_branches"),
]


def defined(tree: ast.Module) -> set[str]:
    """The names a module's own top level assigns or defines."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def imported_from_helpers(tree: ast.Module) -> set[str]:
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module in HELPERS
        for alias in node.names
    }


def used(tree: ast.Module) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


@pytest.mark.parametrize(("module", "name"), COPIES)
def test_a_module_takes_the_helper_from_its_helper_module_instead_of_keeping_a_copy(
    module: str, name: str
) -> None:
    tree = ast.parse((TESTS / module).read_text(encoding="utf-8"))

    assert name not in defined(tree), f"{module} keeps its own copy of {name}"
    if name in used(tree):
        assert name in imported_from_helpers(tree), f"{module} doesn't import {name}"
