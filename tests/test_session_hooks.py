"""What the owner sees when a session starts, and the log of denials (#11)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from agent_hooks import log_denials, session_start
from conftest import World


def run(hook: Any, payload: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert hook.main() == 0
    return out.getvalue()


def context(world: World, monkeypatch: pytest.MonkeyPatch) -> str:
    payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(world.project)}
    output = json.loads(run(session_start, payload, monkeypatch))
    assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    text: str = output["hookSpecificOutput"]["additionalContext"]
    return text


def open_pr(world: World, number: int, labels: list[str]) -> None:
    state = world.gh()
    state["prs"][str(number)] = {
        "number": number,
        "branch": f"{number}-x",
        "title": f"feat: pull request {number}",
        "state": "OPEN",
        "labels": labels,
    }
    world.gh_state.write_text(json.dumps(state))


def test_the_session_starts_with_what_waits_for_the_owner(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.add_issue(10, labels=("task", "ready", "blocked"))
    world.add_issue(11)
    world.add_batch(1, "Lane 1: #10\n")
    open_pr(world, 20, ["risk:high"])
    open_pr(world, 21, [])
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_LANGUAGE", "Spanish (Rioplatense)")

    text = context(world, monkeypatch)

    assert "#10 Issue 10" in text
    assert "#11" not in text
    assert "#20 feat: pull request 20" in text
    assert "#21" not in text
    assert "#1 Batch" in text
    assert "Talk to the owner in Spanish (Rioplatense)" in text
    assert "agent-batch ship" in text


def test_the_session_says_when_github_cant_be_reached(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_GH_DOWN", "1")

    text = context(world, monkeypatch)

    assert "GitHub couldn't be reached" in text


def test_outside_a_project_that_enables_agent_kit_nothing_is_said(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(tmp_path)}
    assert run(session_start, payload, monkeypatch) == ""


def test_a_denial_is_appended_to_the_log(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "hook_event_name": "PermissionDenied",
        "session_id": "s1",
        "cwd": str(world.project),
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf build", "description": "Clean"},
        "tool_use_id": "t1",
        "reason": "Irreversible local destruction",
    }

    assert run(log_denials, payload, monkeypatch) == ""
    assert run(log_denials, {**payload, "tool_use_id": "t2"}, monkeypatch) == ""

    lines = (world.project / ".agent-batch" / "denials.jsonl").read_text().splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["tool"] == "Bash"
    assert entry["input"] == "rm -rf build"
    assert entry["reason"] == "Irreversible local destruction"
    assert entry["session"] == "s1"
