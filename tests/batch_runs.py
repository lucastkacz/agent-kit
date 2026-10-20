"""What tests of `agent-batch run` share: the answers they script and what the run leaves behind."""

from __future__ import annotations

import json
from typing import Any

from conftest import World

BATCH = 1
LIMIT_REACHED = {"error": "Claude usage limit reached."}
APPROVED = {"output": {"verdict": "approved", "findings": []}}
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


def done(**extra: Any) -> dict[str, Any]:
    output = {
        "status": "done",
        "title": "feat: a thing",
        "pr_body": "Body.",
        "message": "",
        "found": [],
    }
    return {"output": {**output, **extra}}


def pr_for(world: World, issue: int) -> dict[str, Any]:
    prs: list[dict[str, Any]] = [
        pr for pr in world.gh()["prs"].values() if pr["branch"].startswith(f"{issue}-")
    ]
    assert len(prs) == 1, prs
    return prs[0]


def events(world: World, batch: int) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{batch}" / "events.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()]


def close_issue(world: World, number: int) -> None:
    """Closes the issue, as GitHub does when the PR that says `Closes #N` merges."""
    state = world.gh()
    state["issues"][str(number)]["state"] = "CLOSED"
    world.gh_state.write_text(json.dumps(state))


def calls_for(world: World, kind: str, number: int) -> list[dict[str, Any]]:
    return [c for c in world.claude_calls() if c["kind"] == kind and c["number"] == number]


def summary(world: World) -> str:
    comments: list[str] = world.gh()["issues"][str(BATCH)]["comments"]
    return comments[-1]


def stop_after_the_first_issue(world: World) -> None:
    """A first run that merges #10 and stops at #11, as a runner stopped mid-batch would."""
    world.add_issue(10)
    world.add_issue(11)
    world.add_batch(BATCH, "Lane 1: #10, #11\n")
    world.script("implement", 11, LIMIT_REACHED)
    world.run("run", str(BATCH))
    assert "merged 1" in summary(world)
    close_issue(world, 10)
