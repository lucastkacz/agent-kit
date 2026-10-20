"""A lane's auto-mode denials, which only the PermissionDenied hook logs, count in the batch (#147).

The fake claude hands a step's `logged` denials to the real hook, with the run's session id, so they
reach `.agent-batch/denials.jsonl` as a lane's do.
"""

from __future__ import annotations

import json

from accept_batch_skill import section
from batch_runs import BATCH
from conftest import World
from lane_denials import CHECK, SESSION, denial, denials_log, events, run_batch
from spec_text import zero_prompts

PUSH = {"command": "git push origin HEAD"}
WATCH = {"command": 'until grep -qE "passed|failed" "$f"; do sleep 2; done; tail -3 "$f"'}
COMMIT = {"command": "git commit -m 'fix: on master'"}
BLOCKED = "protect-master blocked it: commit on a branch of your own, never on master"


def summary(world: World) -> str:
    text: str = world.gh()["issues"][str(BATCH)]["comments"][-1]
    return text


def row_denials(text: str, number: int) -> int:
    row = next(line for line in text.splitlines() if line.startswith(f"| #{number} "))
    return int(row.split("|")[5])


def test_a_lane_runs_hook_logged_denials_count_beside_those_in_its_answer(world: World) -> None:
    other = {"time": "2026-01-01T00:00:00+00:00", "session": "an-interactive-session"}
    denials_log(world).parent.mkdir(parents=True, exist_ok=True)
    denials_log(world).write_text(json.dumps({**other, "tool": "Bash", "input": "ls"}) + "\n")
    logged = [denial("Bash", CHECK), denial("Monitor", WATCH), denial("Bash", CHECK)]

    run_batch(world, {"denials": [denial("Bash", PUSH)], "logged": logged})

    denied = [(event["issue"], event["run"], event["tool"]) for event in events(world)]
    assert sorted(denied) == sorted(
        [(10, "implementation", "Bash")] * 3 + [(10, "implementation", "Monitor")]
    )
    text = summary(world)
    assert row_denials(text, 10) == 4
    assert "**Permission denials:** 4" in text
    assert f"- #10 implementation: Bash `{CHECK['command']}`" in text.splitlines()
    assert f"- #10 implementation: Monitor `{WATCH['command']}`" in text.splitlines()
    assert "`ls`" not in text


def test_a_denial_in_both_the_answer_and_the_hooks_log_counts_once(world: World) -> None:
    block = denial("Bash", COMMIT, reason=BLOCKED)

    run_batch(world, {"denials": [block], "logged": [block]})

    assert [(event["tool"], event["input"]) for event in events(world)] == [("Bash", COMMIT)]
    text = summary(world)
    assert row_denials(text, 10) == 1
    assert "**Permission denials:** 1" in text


def test_each_denial_event_names_the_session_that_the_hooks_log_matches(world: World) -> None:
    run_batch(world, {"denials": [denial("Bash", PUSH)], "logged": [denial("Bash", CHECK)]})

    assert [event.get("session") for event in events(world)] == [SESSION, SESSION]
    entries = [json.loads(line) for line in denials_log(world).read_text().splitlines()]
    assert [entry["session"] for entry in entries] == [SESSION]


def test_accept_batch_reads_an_entry_already_in_the_batchs_log_once() -> None:
    gather = section("Gather everything")
    for token in ("`session`", "`permission_denied` event", "count it once"):
        assert token in gather, (token, gather)


def test_spec_10_1_says_the_hook_logs_a_lanes_auto_mode_denials_that_the_summary_counts() -> None:
    text = zero_prompts()
    assert "those of an interactive session" not in text, text
    for token in ("auto-mode denial", "a lane's", "the batch's summary", "counts them", "once"):
        assert token in text, (token, text)


def test_accept_batch_says_the_hook_logs_a_lanes_denials_that_the_summary_counts() -> None:
    gather = section("Gather everything")
    assert "every interactive session's denials" not in gather, gather
    for token in ("auto-mode denials", "a lane's", "log and summary count"):
        assert token in gather, (token, gather)
