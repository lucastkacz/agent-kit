"""A lane's session counts only the hook's entries of its own runs, in the batch (#147)."""

from __future__ import annotations

import json

from conftest import World
from lane_denials import CHECK, SESSION, denial, denials_log, events, run_batch


def test_an_entry_the_session_logged_before_the_run_started_is_not_counted_again(
    world: World,
) -> None:
    earlier = {"time": "2026-01-01T00:00:00+00:00", "session": SESSION, "tool": "Bash"}
    denials_log(world).parent.mkdir(parents=True, exist_ok=True)
    denials_log(world).write_text(json.dumps({**earlier, "input": "git push"}) + "\n")

    run_batch(world, {"logged": [denial("Bash", CHECK)]})

    assert [event["input"] for event in events(world)] == [{"input": CHECK["command"]}]


def test_a_run_whose_hook_log_is_missing_counts_only_its_answer(world: World) -> None:
    run_batch(world, {"denials": [denial("Bash", CHECK)]})

    assert [event["input"] for event in events(world)] == [CHECK]
    assert not denials_log(world).exists()
