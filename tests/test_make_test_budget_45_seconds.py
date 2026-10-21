"""`make test`'s budget is 45 seconds, and no test was skipped, deleted or weakened for it (#250).

On master 10c336f `make test` took 34-35.5 s with no batch running, over the 30 s SPEC §7.3 gave
it, for the third time; the owner decided on #165 that the budget then becomes 45 s.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPEC.md"
TESTS = ROOT / "tests"
# The test functions in tests/test_*.py on master 10c336f, before #250.
TEST_FUNCTIONS_BEFORE = 716
SKIPS = frozenset({"skip", "skipif", "xfail", "importorskip"})


def time_budgets() -> str:
    """SPEC §7.3's time budgets on one line, so that no check depends on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    section = text.index("### 7.3 Fast and proportionate checks")
    start = text.index("- **Time budgets.**", section)
    end = text.index("\n- **", start + 1)
    return re.sub(r"\s+", " ", text[start:end])


def make_test_row() -> str:
    rows = [
        line
        for line in SPEC.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `make test` |")
    ]
    assert len(rows) == 1, rows
    return rows[0]


def test_spec_7_3_gives_make_test_45_seconds() -> None:
    budgets = time_budgets()
    assert "`make test` finishes in under 45 seconds" in budgets, budgets
    assert "30 seconds" not in budgets, budgets


def test_specs_table_of_make_targets_gives_make_test_45_seconds() -> None:
    assert (
        make_test_row() == "| `make test` | The small and medium tests (§7.3). Under 45 seconds. |"
    )


def modules_with_tests() -> list[Path]:
    return sorted(TESTS.glob("test_*.py"))


def skipping_calls(tree: ast.AST) -> list[int]:
    """The lines that skip a test or expect it to fail: `pytest.skip(...)`, `pytest.mark.xfail`."""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in SKIPS
    ]


def test_no_test_is_skipped_or_expected_to_fail() -> None:
    sources = sorted(path for path in TESTS.rglob("*.py") if "__pycache__" not in path.parts)
    found = [
        f"{path.relative_to(ROOT)}:{line}"
        for path in sources
        for line in skipping_calls(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert not found, found


def test_the_suite_keeps_every_test_function_it_had_before() -> None:
    count = sum(
        isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        for path in modules_with_tests()
        for node in ast.parse(path.read_text(encoding="utf-8")).body
    )
    assert count >= TEST_FUNCTIONS_BEFORE, count


def module_constant(module: str, name: str) -> object:
    tree = ast.parse((TESTS / module).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{module} has no {name}")


def test_the_slowest_tests_keep_the_waits_they_check_with() -> None:
    # Their time is a wait on purpose: a runner that writes late, and a run past its timeout.
    assert module_constant("test_token_count_snapshot.py", "LATE") == 0.3
    timed_out = (TESTS / "test_lane_hook_denials_timed_out.py").read_text(encoding="utf-8")
    for token in ("implement_timeout=2", '"sleep": 6'):
        assert token in timed_out, token
