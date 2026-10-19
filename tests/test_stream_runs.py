"""Runs are read from `claude`'s stream of messages as they were from its single answer (#107)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from agent_batch.core import prompts, results
from agent_batch.core.config import Config
from agent_batch.core.env import clean_env
from agent_batch.core.model import Denial
from agent_batch.shell import claude
from agent_batch.shell.claude import Claude
from conftest import World

INIT = {"type": "system", "subtype": "init", "session_id": "s1"}
TOOL_USE = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": "First the file."},
            {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "/p/a.py"}},
        ],
    },
    "session_id": "s1",
}
TOOL_RESULT = {
    "type": "user",
    "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1"}]},
    "session_id": "s1",
}
DONE: dict[str, Any] = {
    "status": "done",
    "title": "feat: x",
    "pr_body": "Body.",
    "message": "",
    "found": [],
}
READ = {"name": "Read", "input": {"file_path": "README.md"}}


def stream(*messages: dict[str, Any]) -> str:
    return "".join(json.dumps(message) + "\n" for message in messages)


def test_runs_ask_claude_for_a_stream_of_its_messages() -> None:
    argv = claude.command("Work issue #1.", {}, claude.IMPLEMENTER)

    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in argv


def test_a_streams_answer_denials_cost_and_session_id_come_from_its_result_message() -> None:
    result = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "",
        "session_id": "s1",
        "total_cost_usd": 0.25,
        "permission_denials": [
            {"tool_name": "Bash", "tool_use_id": "t2", "tool_input": {"command": "git push"}}
        ],
        "structured_output": DONE,
    }

    run = results.parse_run(stream(INIT, TOOL_USE, TOOL_RESULT, result))

    assert run.error is None
    assert run.data == DONE
    assert run.session_id == "s1"
    assert run.cost_usd == 0.25
    assert run.denials == (Denial("Bash", {"command": "git push"}),)
    assert run.limit_reached is False


def test_a_stream_that_ends_at_the_usage_limit_stops_as_today() -> None:
    limit = {
        "type": "result",
        "is_error": True,
        "result": "Claude usage limit reached. Resets 5pm.",
    }

    run = results.parse_run(stream(INIT, TOOL_USE, TOOL_RESULT, limit))

    assert run.data is None
    assert run.limit_reached is True


def test_a_streamed_run_past_its_timeout_ends_as_today(world: World) -> None:
    world.script("implement", 10, {"tools": [READ], "sleep": 5})
    runner = Claude(clean_env(os.environ), Config(implement_timeout=1))
    started = time.monotonic()

    run = runner.implement(world.project, prompts.implement(10), None)

    assert run.error == "the run took longer than 1 seconds"
    assert run.data is None
    assert time.monotonic() - started < 4


def test_a_streamed_run_that_reaches_the_usage_limit_ends_as_today(world: World) -> None:
    world.script("review", 10, {"tools": [READ], "error": "Claude usage limit reached."})
    runner = Claude(clean_env(os.environ), Config())

    run = runner.review(world.project, prompts.review(10))

    assert run.data is None
    assert run.limit_reached is True
