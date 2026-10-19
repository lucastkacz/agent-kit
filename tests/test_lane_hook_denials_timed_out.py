"""A resumed run past its timeout still counts the denials the hook logged for it (#147)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agent_batch import cli
from conftest import World
from test_lane_hook_denials import BATCH, CHECK, denial, events
from test_skill_accept_batch import section


def test_a_resumed_run_past_its_timeout_still_records_its_hook_logged_denials(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = cli._config
    monkeypatch.setattr(cli, "_config", lambda **kw: replace(config(**kw), implement_timeout=2))
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10 #11\n")
    # #11 resumes #10's session, logs a denial and runs past the timeout; a fresh run then ends it.
    world.script("implement", 11, {"logged": [denial("Bash", CHECK)], "sleep": 6}, {})
    world.run("run", str(BATCH))

    implements = [call for call in world.claude_calls() if call["kind"] == "implement"]
    assert [call["number"] for call in implements] == [10, 11, 11], implements
    assert "--resume" in implements[1]["argv"], implements
    recorded = [(event["issue"], event["input"], event["session"]) for event in events(world)]
    assert recorded == [(11, {"input": CHECK["command"]}, "session-implement-11-0")]


def test_accept_batch_matches_an_entry_to_the_text_the_hook_makes_of_an_input() -> None:
    gather = section("Gather everything")
    for token in ("first 300 characters", "`command`, `file_path`, `url` or `pattern`", "json"):
        assert token in gather, (token, gather)
