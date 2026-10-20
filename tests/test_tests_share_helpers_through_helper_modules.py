"""Tests share their helpers through helper modules, never through other test modules (#205).

Importing a test module runs its module-level code and hides which tests depend on which,
so a change to one test file can break another's.
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent
# The test directories on pytest's and mypy's path, where `import <name>` finds a module.
ON_PATH = (TESTS, TESTS / "fakes", TESTS / "contract")


def sources() -> list[Path]:
    return sorted(path for path in TESTS.rglob("*.py") if "__pycache__" not in path.parts)


def imported_modules(tree: ast.AST) -> list[tuple[int, str]]:
    """Each absolute import's line and top-level module."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name.split(".")[0]) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module.split(".")[0]))
    return found


def local_module(name: str) -> Path | None:
    for directory in ON_PATH:
        candidate = directory / f"{name}.py"
        if candidate.exists():
            return candidate
    return None


def defines_tests(tree: ast.Module) -> bool:
    return any(
        (isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
        or (isinstance(node, ast.ClassDef) and node.name.startswith("Test"))
        for node in tree.body
    )


def test_no_module_in_the_tests_imports_a_test_module() -> None:
    wrong = [
        f"{path.relative_to(TESTS.parent)}:{line} imports {module}"
        for path in sources()
        for line, module in imported_modules(ast.parse(path.read_text(encoding="utf-8")))
        if module.startswith("test_")
    ]

    assert not wrong, "move what these share into a helper module:\n" + "\n".join(wrong)


def test_the_modules_that_tests_share_are_helper_modules_without_tests() -> None:
    shared = {
        module
        for path in sources()
        for module in (
            local_module(name)
            for _, name in imported_modules(ast.parse(path.read_text(encoding="utf-8")))
        )
        if module is not None
    }
    wrong = [
        f"{module.relative_to(TESTS.parent)} is shared but is a test module or holds tests"
        for module in sorted(shared)
        if module.name.startswith("test_")
        or defines_tests(ast.parse(module.read_text(encoding="utf-8")))
    ]

    assert not wrong, "\n".join(wrong)
