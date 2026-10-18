"""Fails when a Python file or function goes over the size limits in SPEC §8.2."""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

MAX_FILE_LINES = 400
MAX_FUNCTION_LINES = 50


def file_problems(path: Path) -> Iterator[str]:
    """The limits that one file breaks, as `path:line: message` lines."""
    source = path.read_text(encoding="utf-8")
    lines = len(source.splitlines())
    if lines > MAX_FILE_LINES:
        yield f"{path}:1: the file has {lines} lines (the limit is {MAX_FILE_LINES})"
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > MAX_FUNCTION_LINES:
                yield (
                    f"{path}:{node.lineno}: {node.name} has {length} lines "
                    f"(the limit is {MAX_FUNCTION_LINES})"
                )


def python_files(roots: list[str]) -> Iterator[Path]:
    for root in map(Path, roots):
        yield from [root] if root.is_file() else sorted(root.rglob("*.py"))


def main(roots: list[str]) -> int:
    problems = [problem for path in python_files(roots) for problem in file_problems(path)]
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
