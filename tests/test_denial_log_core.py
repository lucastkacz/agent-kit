"""How the runner reads the PermissionDenied hook's log for a run's session (#147)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from agent_batch.core import denial_log
from agent_batch.core.model import Denial
from agent_hooks import log_denials

NOW = datetime(2026, 10, 19, tzinfo=UTC)
CHECK: dict[str, object] = {"command": "make check", "description": "Run the checks"}


def line(session: str, tool: str, tool_input: dict[str, object]) -> str:
    payload = {"session_id": session, "tool_name": tool, "tool_input": tool_input}
    return json.dumps(log_denials.entry(payload, "Classifier unavailable", NOW)) + "\n"


@pytest.mark.parametrize(
    "tool_input",
    [
        CHECK,
        {"file_path": "/project/a.txt", "content": "hi"},
        {"url": "https://example.com"},
        {"pattern": "TODO", "path": "src"},
        {"question": "x" * 400},
        {"command": "echo " + "y" * 400},
    ],
)
def test_its_summary_of_an_input_is_the_text_the_hook_logs(tool_input: dict[str, object]) -> None:
    logged = json.loads(line("s1", "Bash", tool_input))["input"]

    assert denial_log.summary(tool_input) == logged


def test_it_reads_only_the_sessions_entries_and_skips_a_cut_line() -> None:
    text = line("other", "Bash", CHECK) + '{"session": "s1", "to' + "\n" + line("s1", "Bash", CHECK)

    assert denial_log.logged(text, "s1") == [Denial("Bash", {"input": "make check"}, "s1")]


def test_an_entry_without_a_tool_or_input_still_counts() -> None:
    text = json.dumps({"session": "s1", "tool": None, "input": 3}) + "\n"

    assert denial_log.logged(text, "s1") == [Denial("unknown tool", {"input": ""}, "s1")]


def test_each_logged_entry_matches_one_denial_of_the_answer_at_most() -> None:
    answer = [Denial("Bash", CHECK), Denial("Write", {"file_path": "/a"})]
    entries = denial_log.logged(line("s1", "Bash", CHECK) * 2, "s1")

    run = denial_log.combined(answer, entries, "s1")

    assert run == (
        Denial("Bash", CHECK, "s1"),
        Denial("Write", {"file_path": "/a"}, "s1"),
        Denial("Bash", {"input": "make check"}, "s1"),
    )
