"""An agent merges a pull request only when the owner asks for that one; batch runs never (#62)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from agent_batch.shell import claude
from agent_hooks import session_start
from conftest import World


def session_context(world: World, monkeypatch: pytest.MonkeyPatch) -> str:
    payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(world.project)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert session_start.main() == 0
    text: str = json.loads(out.getvalue())["hookSpecificOutput"]["additionalContext"]
    return text


def test_the_session_says_agents_merge_a_pull_request_only_when_the_owner_asks_for_that_one(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = session_context(world, monkeypatch)

    assert "merge a pull request only when the owner asks for that one in the chat" in text
    assert "never merge" not in text.lower()


@pytest.mark.parametrize("options", [claude.IMPLEMENTER, claude.REVIEWER])
def test_every_batch_run_is_denied_gh_pr_and_gh_api_so_it_cannot_merge(
    options: tuple[str, ...],
) -> None:
    line = claude.command("Work issue #1.", {}, options)
    settings = Path(line[line.index("--settings") + 1])

    deny = json.loads(settings.read_text(encoding="utf-8"))["permissions"]["deny"]

    assert "Bash(gh pr *)" in deny
    assert "Bash(gh api *)" in deny
