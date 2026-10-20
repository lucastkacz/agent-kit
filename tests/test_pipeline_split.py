"""`pipeline.py` leaves room under the 400-line limit, its merge steps in their own module (#210).

The runner's behavior stays as it was: the rest of the suite checks it (small tests).
"""

from __future__ import annotations

import ast
from pathlib import Path

RUNNER = Path(__file__).parents[1] / "plugin" / "runner" / "agent_batch"
MERGE_AND_RESOLVE = {"classify", "hold", "_merge", "_finish", "_wait", "_resolve"}


def functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_pipeline_has_at_most_350_lines() -> None:
    lines = len((RUNNER / "pipeline.py").read_text().splitlines())

    assert lines <= 350, f"pipeline.py has {lines} lines"


def test_the_merge_and_resolve_steps_live_in_a_module_of_their_own() -> None:
    landing = RUNNER / "landing.py"

    assert landing.exists(), "there's no landing.py for the merge-and-resolve steps"
    assert functions(landing) >= MERGE_AND_RESOLVE
    assert not functions(RUNNER / "pipeline.py") & MERGE_AND_RESOLVE
