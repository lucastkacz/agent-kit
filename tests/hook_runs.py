"""What tests of the plugin's hooks share: running a hook on a payload, and a session's start."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from agent_hooks import session_start
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
