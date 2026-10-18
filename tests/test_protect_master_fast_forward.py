"""protect-master lets a fast-forward of `master` through, and logs what it blocks (#78)."""

from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path

import pytest

from agent_hooks import protect_master
from agent_hooks.commands import git_calls
from conftest import ENABLED, git

HERE = Path("/repo")


def refusal(command: str, branch: str) -> str | None:
    found = git_calls(command, HERE)
    reasons = [protect_master.refusal(call, lambda _: branch) for call in found]
    return next((reason for reason in reasons if reason), None)


@pytest.mark.parametrize(
    "command",
    [
        "git merge --ff-only origin/master",
        "git fetch origin && git merge --ff-only origin/master",
        "git merge --ff-only 12-export",
    ],
)
def test_a_fast_forward_merge_on_master_runs(command: str) -> None:
    assert refusal(command, "master") is None
    assert refusal(command, "main") is None


@pytest.mark.parametrize(
    "command",
    ["git merge origin/master", "git merge --no-ff origin/master", "git merge --ff 12-export"],
)
def test_a_merge_without_ff_only_on_master_is_still_blocked(command: str) -> None:
    assert refusal(command, "master")
    assert refusal(command, "main")


def project_on_master(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    git(tmp_path, "init", "--quiet", "-b", "master", str(repo))
    git(repo, "commit", "--quiet", "--allow-empty", "-m", "chore: start")
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text(ENABLED)
    return repo


def run_hook(command: str, cwd: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "s1",
        "cwd": str(cwd),
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "Commit"},
        "tool_use_id": "t1",
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert protect_master.main() == 0
    return out.getvalue()


def test_each_blocked_command_is_logged_with_its_time_session_tool_input_and_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = project_on_master(tmp_path)

    denied = json.loads(run_hook("git commit -m x", repo, monkeypatch))
    assert run_hook("git status", repo, monkeypatch) == ""

    reason = denied["hookSpecificOutput"]["permissionDecisionReason"]
    lines = (repo / ".agent-batch" / "denials.jsonl").read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert set(entry) == {"time", "session", "tool", "input", "reason"}
    assert datetime.fromisoformat(entry["time"]).tzinfo is not None
    assert entry["session"] == "s1"
    assert entry["tool"] == "Bash"
    assert entry["input"] == "git commit -m x"
    assert "protect-master" in entry["reason"]
    assert reason in entry["reason"]
