"""The `check` target's complexipy step names what goes over the limit (integration)."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TOO_COMPLEX = """\
def tangled(a, b, c, d):
    for i in a:
        if i:
            for j in b:
                if j:
                    for k in c:
                        if k and d or c:
                            if d:
                                while d:
                                    if a:
                                        break
    return 1


def simple():
    return 2
"""


def _complexipy_step(paths: Path) -> subprocess.CompletedProcess[str]:
    dry_run = subprocess.run(
        ["make", "-n", "check", f"PYTHON_PATHS={paths}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    [command] = [line for line in dry_run.stdout.splitlines() if "complexipy" in line]
    return subprocess.run(
        shlex.split(command), cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_a_function_over_the_limit_is_named_with_its_complexity(tmp_path: Path) -> None:
    (tmp_path / "tangled.py").write_text(TOO_COMPLEX)

    step = _complexipy_step(tmp_path)

    assert step.returncode != 0
    output = step.stdout + step.stderr
    assert "tangled 47" in output
    assert "simple" not in output


def test_no_table_of_functions_when_every_function_is_under_the_limit(
    tmp_path: Path,
) -> None:
    (tmp_path / "simple.py").write_text("def simple():\n    return 2\n")

    step = _complexipy_step(tmp_path)

    assert step.returncode == 0
    assert "simple" not in step.stdout + step.stderr
