"""The plugin acts only in projects that enable it (#14)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from agent_hooks import log_denials, protect_master, session_start
from agent_hooks.repo import enabled_here
from conftest import git


def settings(root: Path, name: str, content: str) -> None:
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude" / name).write_text(content)


@pytest.mark.parametrize(
    ("name", "content", "enabled"),
    [
        ("settings.json", '{"enabledPlugins": {"agent-kit@agent-kit": true}}', True),
        ("settings.local.json", '{"enabledPlugins": {"agent-kit@my-fork": true}}', True),
        ("settings.json", '{"enabledPlugins": {"agent-kit@agent-kit": false}}', False),
        ("settings.json", '{"enabledPlugins": {"other@agent-kit": true}}', False),
        ("settings.json", "{not json", False),
    ],
)
def test_a_project_enables_agent_kit_in_its_own_settings(
    tmp_path: Path, name: str, content: str, enabled: bool
) -> None:
    settings(tmp_path, name, content)
    assert enabled_here(tmp_path) is enabled


def test_a_folder_without_settings_doesnt_enable_it(tmp_path: Path) -> None:
    assert enabled_here(tmp_path) is False


def run(hook: Any, payload: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert hook.main() == 0
    return out.getvalue()


def test_the_hooks_do_nothing_where_agent_kit_isnt_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init", "--quiet", "-b", "master")
    git(tmp_path, "commit", "--quiet", "--allow-empty", "-m", "chore: start")
    cwd = str(tmp_path)

    commit = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": cwd}
    assert run(protect_master, commit, monkeypatch) == ""
    assert run(session_start, {"source": "startup", "cwd": cwd}, monkeypatch) == ""
    denial = {"tool_name": "Bash", "tool_input": {"command": "rm -rf x"}, "cwd": cwd}
    assert run(log_denials, {**denial, "reason": "r"}, monkeypatch) == ""
    assert not (tmp_path / ".agent-batch").exists()

    settings(tmp_path, "settings.json", '{"enabledPlugins": {"agent-kit@agent-kit": true}}')
    assert "deny" in run(protect_master, commit, monkeypatch)
