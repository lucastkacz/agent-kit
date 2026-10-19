"""Batch #187's new tests break only when their behavior breaks, on any computer (#196)."""

from __future__ import annotations

import ast
import io
import os
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

from agent_batch.shell import system

TESTS = Path(__file__).parent
ROOT = TESTS.parent
COMPLEXIPY_TEST = "tests/test_check_names_complex_functions.py"
OVER_THE_LIMIT = "test_a_function_over_the_limit_is_named_with_its_complexity"
UNDER_THE_LIMIT = "test_no_table_of_functions_when_every_function_is_under_the_limit"
RECORDING_TEST = "test_the_recorded_streams_messages_each_carry_their_id_and_tokens"
# A `uv run complexipy` that prints what the test gives it and exits as it says.
FAKE_UV = """#!/bin/sh
printf '%s\\n' "$FAKE_COMPLEXIPY_OUTPUT"
exit "$FAKE_COMPLEXIPY_EXIT"
"""


def _complexipy_test_passes(tmp_path: Path, test: str, output: str, exit_code: int) -> bool:
    """Runs one of the complexipy step's tests with a complexipy that prints `output`."""
    fakes = tmp_path / "bin"
    fakes.mkdir()
    (fakes / "uv").write_text(FAKE_UV)
    (fakes / "uv").chmod(0o755)
    env = {
        "PATH": f"{fakes}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "FAKE_COMPLEXIPY_OUTPUT": output,
        "FAKE_COMPLEXIPY_EXIT": str(exit_code),
    }
    pytest_run = [sys.executable, "-m", "pytest", f"{COMPLEXIPY_TEST}::{test}"]
    done = subprocess.run(
        [*pytest_run, "-p", "no:cacheprovider", "--basetemp", str(tmp_path / "pytest")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def test_the_complexipy_test_passes_when_an_upgrade_scores_the_function_differently(
    tmp_path: Path,
) -> None:
    assert _complexipy_test_passes(tmp_path, OVER_THE_LIMIT, "/x/tangled.py tangled 52", 1)


def test_the_complexipy_test_fails_when_the_function_is_named_without_a_score(
    tmp_path: Path,
) -> None:
    assert not _complexipy_test_passes(tmp_path, OVER_THE_LIMIT, "/x/tangled.py tangled", 1)


@pytest.mark.parametrize(
    ("test", "output", "exit_code"),
    [
        (OVER_THE_LIMIT, "/x/tangled.py tangled 52\n/x/tangled.py simple 0", 1),
        (UNDER_THE_LIMIT, "/x/simple.py simple 0", 0),
    ],
)
def test_the_complexipy_test_fails_when_the_step_prints_a_row_for_a_function_under_the_limit(
    tmp_path: Path, test: str, output: str, exit_code: int
) -> None:
    assert not _complexipy_test_passes(tmp_path, test, output, exit_code)


def _imports(path: Path) -> list[tuple[str, str]]:
    """The (module, name) pairs a file imports; `import m` gives (m, "")."""
    pairs: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            pairs += [(alias.name, "") for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            pairs += [(node.module, alias.name) for alias in node.names]
    return pairs


def _called_names(tree: ast.AST) -> set[str]:
    calls = (node.func for node in ast.walk(tree) if isinstance(node, ast.Call))
    return {func.id for func in calls if isinstance(func, ast.Name)}


def _test_helpers(path: Path) -> set[tuple[str, str]]:
    """What a file imports from a helper module of the tests: one that holds no tests."""
    return {
        (module, name)
        for module, name in _imports(path)
        if (TESTS / f"{module}.py").exists() and not module.startswith(("test_", "conftest"))
    }


@pytest.mark.parametrize("name", ["test_running_cost_edges.py", "test_recorded_stream_check.py"])
def test_the_recorded_streams_tests_import_no_other_test_module(name: str) -> None:
    imported = [module for module, _ in _imports(TESTS / name) if module.startswith("test_")]

    assert imported == [], f"{name} imports the test module {imported}"


def test_the_recordings_test_and_its_acceptance_tests_call_one_helper() -> None:
    recording = TESTS / "test_running_cost_edges.py"
    acceptance = TESTS / "test_recorded_stream_check.py"
    tree = ast.parse(recording.read_text(encoding="utf-8"))
    [test] = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == RECORDING_TEST
    ]
    acceptance_calls = _called_names(ast.parse(acceptance.read_text(encoding="utf-8")))

    shared = _test_helpers(recording) & _test_helpers(acceptance)
    called = {name for _, name in shared if name in _called_names(test) & acceptance_calls}
    assert called, "the recording's test and its acceptance tests call no helper they share"


@pytest.mark.usefixtures("world")
def test_the_fake_systemd_inhibits_command_lasts_without_an_error(
    capfd: pytest.CaptureFixture[str],
) -> None:
    hold = system.keep_awake("linux")
    assert hold is not None, "the fake systemd-inhibit held nothing"
    try:
        ended = hold.wait(timeout=2)
    except subprocess.TimeoutExpired:
        ended = None
    finally:
        hold.terminate()
        hold.wait()

    assert ended is None, f"its command ended at once, with {ended}"
    assert capfd.readouterr().err == ""


def _comment_blocks(source: str) -> list[tuple[int, str]]:
    """Each run of whole-line comments, as the line it ends on and its text in lowercase."""
    blocks: list[tuple[int, str]] = []
    lines = source.splitlines()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        row = token.start[0]
        if token.type != tokenize.COMMENT or not lines[row - 1].lstrip().startswith("#"):
            continue
        text = token.string.lstrip("# ").lower()
        if blocks and blocks[-1][0] == row - 1:
            blocks[-1] = (row, f"{blocks[-1][1]} {text}")
        else:
            blocks.append((row, text))
    return blocks


def test_a_comment_beside_the_shell_fakes_says_how_to_wait_on_a_fake() -> None:
    source = (TESTS / "conftest.py").read_text(encoding="utf-8")
    first_fake = source.splitlines().index('CAFFEINATE = """#!/bin/sh') + 1
    [(_, above)] = [block for block in _comment_blocks(source) if block[0] == first_fake - 1]

    assert "at least 2 s" in above, "it doesn't say how long to allow a fake to start"
    assert "how it ended" in above, "it doesn't say to check how the fake ended"
    assert "not a file it writes when it starts" in above
