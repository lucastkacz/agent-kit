"""protect-master's edges: git's last fast-forward option wins, and a log it can't write (#78)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from agent_hooks import protect_master
from agent_hooks.commands import git_calls
from conftest import ENABLED, git


def refusal(command: str, branch: str) -> str | None:
    found = git_calls(command, Path("/repo"))
    reasons = [protect_master.refusal(call, lambda _: branch) for call in found]
    return next((reason for reason in reasons if reason), None)


def test_a_later_no_ff_undoes_ff_only_so_the_merge_is_blocked() -> None:
    assert refusal("git merge --ff-only --no-ff origin/master", "master")
    assert refusal("git merge --no-ff --ff-only origin/master", "master") is None


def test_the_refusal_of_a_merge_on_master_names_the_fast_forward() -> None:
    assert "git merge --ff-only origin/master" in str(refusal("git merge x", "master"))
    assert "--ff-only" not in str(refusal("git commit -m x", "master"))


def test_a_log_that_cant_be_written_still_blocks_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    git(tmp_path, "init", "--quiet", "-b", "master", str(repo))
    git(repo, "commit", "--quiet", "--allow-empty", "-m", "chore: start")
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text(ENABLED)
    (repo / ".agent-batch").write_text("a file where the log's folder goes")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": str(repo)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    assert protect_master.main() == 0

    assert json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny"
