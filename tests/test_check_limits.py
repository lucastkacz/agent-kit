"""The size limits check (small tests)."""

from __future__ import annotations

from pathlib import Path

import check_limits


def test_a_long_file_and_a_long_function_are_reported(tmp_path: Path) -> None:
    long_function = "def f():\n" + "    x = 1\n" * 60
    (tmp_path / "long.py").write_text(long_function + "\n" * 400)
    (tmp_path / "fine.py").write_text("def g():\n    return 1\n")

    problems = list(check_limits.file_problems(tmp_path / "long.py"))

    assert len(problems) == 2
    assert "the file has 461 lines" in problems[0]
    assert "f has 61 lines" in problems[1]
    assert check_limits.main([str(tmp_path / "fine.py")]) == 0
    assert check_limits.main([str(tmp_path)]) == 1
