"""Implementation, fix and resolve runs log their cost and tokens, which price a resume (#217)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from conftest import World

BATCH = 1
LIMIT_REACHED = {"error": "Claude usage limit reached."}
CHANGES = {
    "output": {
        "verdict": "changes",
        "findings": [
            {
                "severity": "high",
                "origin": "new",
                "location": "a.py:1",
                "problem": "It breaks.",
                "suggestion": "Fix.",
            }
        ],
    }
}


def read(tokens: int) -> dict[str, object]:
    return {"name": "Read", "input": {"file_path": "README.md"}, "tokens": tokens}


def events(world: World, event: str) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    return [record for record in records if record["event"] == event]


def status_row(world: World, capsys: pytest.CaptureFixture[str], issue: int) -> str:
    capsys.readouterr()
    assert world.run("status") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if f"#{issue}" in line]
    assert len(rows) == 1, rows
    return rows[0]


def close_issue(world: World, number: int) -> None:
    """Closes the issue, as GitHub does when the PR that says `Closes #N` merges."""
    state = world.gh()
    state["issues"][str(number)]["state"] = "CLOSED"
    world.gh_state.write_text(json.dumps(state))


def test_each_implementation_fix_and_resolve_run_logs_a_run_ended_event_with_its_cost_and_tokens(
    world: World,
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, {"files": ["shared.txt"], "tools": [read(2000)], "cost": 0.2})
    world.script("review", 10, CHANGES, {}, {})
    world.script("fix", 10, {"tools": [read(300)], "cost": 0.03})
    world.script("resolve", 10, {"tools": [read(100)], "cost": 0.01})
    conflict = {"file": "shared.txt", "content": "another lane\n"}
    world.pr_views(
        "10-issue-10",
        {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": conflict},
        {"state": "OPEN", "mergeable": "MERGEABLE"},
    )

    assert world.run("run", str(BATCH)) == 0

    ended = [
        (run["issue"], run["kind"], run["cost_usd"], run["tokens"])
        for run in events(world, "run_ended")
    ]
    assert ended == [
        (10, "implementation", pytest.approx(0.2), 2000),
        (10, "fix", pytest.approx(0.03), 300),
        (10, "resolve", pytest.approx(0.01), 100),
    ]


def test_a_resumed_batch_starts_at_the_rate_of_all_its_earlier_runs_not_just_its_reviews(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    # Only the implementation of #10 has tokens: its review's, logged without any, set no rate.
    world.script("implement", 10, {"tools": [read(2000)], "cost": 0.20})
    # The first run stops at #11; the second one starts #11 again, with no run of its own ended.
    world.script("implement", 11, LIMIT_REACHED, {"tools": [read(500)], "snapshot": True})
    world.run("run", str(BATCH))
    close_issue(world, 10)

    assert world.run("run", str(BATCH)) == 0

    [snapshot] = world.status_snapshots()
    world.restore_status(snapshot)
    found = status_row(world, capsys, 11)
    assert "~$0.05 (estimate)" in found
    assert "tokens" not in found
