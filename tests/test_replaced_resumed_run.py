"""A resumed run that returns no data and is replaced keeps its denials and cost (#51)."""

from __future__ import annotations

import json
from typing import Any

from batch_runs import BATCH, events
from conftest import World

PUSH = {"command": "git push origin HEAD"}
FORCE = {"command": "git push --force origin HEAD"}
# The fake claude's answered runs cost $0.01 each; the replaced run's cost stands out from theirs.
REPLACED_COST = 1.00


def denial(tool_input: dict[str, Any], use: str) -> dict[str, Any]:
    return {"tool_name": "Bash", "tool_use_id": use, "tool_input": tool_input}


def batch_with_a_replaced_resumed_run(world: World) -> None:
    """#11 resumes #10's session; that run fails with a denial and a fresh one replaces it."""
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    replaced = {
        "type": "result",
        "subtype": "error_during_execution",
        "is_error": True,
        "result": "the session ended without an answer",
        "session_id": "session-implement-11-resumed",
        "total_cost_usd": REPLACED_COST,
        "permission_denials": [denial(FORCE, "t1")],
    }
    world.script("implement", 11, {"raw": json.dumps(replaced)}, {"denials": [denial(PUSH, "t2")]})
    world.run("run", str(BATCH))


def test_the_event_log_has_the_denials_of_the_replaced_run_and_of_the_fresh_one(
    world: World,
) -> None:
    batch_with_a_replaced_resumed_run(world)

    implement_11 = [
        c for c in world.claude_calls() if c["kind"] == "implement" and c["number"] == 11
    ]
    assert ["--resume" in call["argv"] for call in implement_11] == [True, False]
    denied = [
        {key: event.get(key) for key in ("issue", "run", "tool", "input")}
        for event in events(world, BATCH)
        if event["event"] == "permission_denied"
    ]
    assert denied == [
        {"issue": 11, "run": "implementation", "tool": "Bash", "input": FORCE},
        {"issue": 11, "run": "implementation", "tool": "Bash", "input": PUSH},
    ]


def test_the_summary_lists_and_counts_the_denials_of_both_runs(world: World) -> None:
    batch_with_a_replaced_resumed_run(world)

    summary: str = world.gh()["issues"][str(BATCH)]["comments"][-1]
    lines = summary.splitlines()
    assert "- #11 implementation: Bash `git push --force origin HEAD`" in lines
    assert "- #11 implementation: Bash `git push origin HEAD`" in lines
    assert "**Permission denials:** 2" in lines
    row_11 = next(line for line in lines if line.startswith("| #11 |"))
    assert row_11.split("|")[5].strip() == "2"


def test_the_notional_cost_adds_the_replaced_run_and_the_fresh_one(world: World) -> None:
    batch_with_a_replaced_resumed_run(world)

    summary: str = world.gh()["issues"][str(BATCH)]["comments"][-1]
    # #10's implementation and review, then #11's replaced run, its fresh run and its review.
    expected = 0.01 + 0.01 + REPLACED_COST + 0.01 + 0.01
    assert f"**Notional cost:** ${expected:.2f}" in summary.splitlines()
