"""The status line's edges: where git's files say little, or nothing (#108)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from agent_batch import cli
from agent_batch.core import progress
from agent_batch.shell import checkout
from conftest import World, git


def test_a_detached_head_shows_the_start_of_its_commit(world: World) -> None:
    commit = git(world.project, "rev-parse", "HEAD").strip()
    git(world.project, "switch", "--quiet", "--detach")

    found = checkout.find(world.project)

    assert found == checkout.Checkout(world.project, commit[:7])


def test_outside_a_repository_there_is_no_checkout(tmp_path: Path) -> None:
    assert checkout.find(tmp_path) is None


def test_a_git_file_that_names_no_folder_is_no_checkout(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("not a pointer\n")

    assert checkout.find(tmp_path) is None


def test_outside_a_repository_the_status_line_says_nothing_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)})))

    assert cli.main(["status", "--line"]) == 0
    assert capsys.readouterr().out == "nothing running\n"


def test_without_a_cwd_on_stdin_the_status_line_uses_its_own_folder(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

    assert world.run("status", "--line") == 0
    assert capsys.readouterr().out == "nothing running · master\n"


def test_the_session_cwd_is_read_only_from_a_json_object_with_a_text_cwd() -> None:
    assert progress.session_cwd('{"cwd": "/work"}') == "/work"
    for text in ("[]", '{"cwd": 3}', '{"cwd": ""}', "{}", "nope"):
        assert progress.session_cwd(text) is None


def test_a_branch_with_a_control_character_cant_garble_the_terminal() -> None:
    assert progress.line([], 0.0, "x\x1b[2Jy") == "nothing running · x?[2Jy\n"


def test_the_last_steps_have_short_names() -> None:
    rows = [
        progress.Row("batch-1", 1, progress.LaneState(5, progress.PULL_REQUEST, 0.0, 2, 1)),
        progress.Row("batch-1", 2, progress.LaneState(6, progress.RISK_AND_MERGE, 0.0, 2, 3)),
    ]

    assert progress.line(rows, 0.0, "master") == "L1 #5 PR 1/2 · L2 #6 merge 3/3\n"
