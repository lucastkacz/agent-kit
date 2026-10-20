"""A run that ends without its result still counts the denials the hook logged for it (#147)."""

from __future__ import annotations

import json

from agent_batch.core import denial_log, results
from agent_batch.core.model import Denial
from conftest import World
from lane_denials import CHECK, SESSION, denial, events, run_batch


def test_a_run_that_dies_without_a_result_still_records_its_hook_logged_denials(
    world: World,
) -> None:
    run_batch(world, {"logged": [denial("Bash", CHECK)], "raw": "", "code": 1})

    recorded = [(event["tool"], event["input"], event["session"]) for event in events(world)]
    assert recorded == [("Bash", {"input": CHECK["command"]}, SESSION)]


def test_the_streams_first_message_names_the_session_of_a_run_cut_short() -> None:
    init = json.dumps({"type": "system", "subtype": "init", "session_id": "s1"})

    assert results.stream_session("not json\n" + init + "\n") == "s1"
    assert results.stream_session("") is None


def test_an_input_the_hook_couldnt_read_matches_the_answers_unreadable_one() -> None:
    entries = denial_log.logged(json.dumps({"session": "s1", "tool": "Bash", "input": ""}), "s1")

    assert denial_log.combined([Denial("Bash", {})], entries, "s1") == (Denial("Bash", {}, "s1"),)
