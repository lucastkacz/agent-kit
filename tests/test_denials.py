"""Each permission denial of a batch, in its event log and its summary (#30, medium tests)."""

from __future__ import annotations

import json
from typing import Any

from conftest import World

BATCH = 1
PUSH = {"command": "git push origin HEAD"}
LONG = {"command": "echo " + "x" * 300}
WRITE = {"file_path": "/project/marker.txt", "content": "hi"}


def denial(tool: str, tool_input: dict[str, Any], use: str) -> dict[str, Any]:
    return {"tool_name": tool, "tool_use_id": use, "tool_input": tool_input}


def batch_with_denials(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script(
        "implement", 10, {"denials": [denial("Bash", PUSH, "t1"), denial("Bash", LONG, "t2")]}
    )
    world.script(
        "review",
        10,
        {
            "output": {"verdict": "approved", "findings": []},
            "denials": [denial("Write", WRITE, "t3")],
        },
    )
    world.run("run", str(BATCH))


def events(world: World) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_each_denial_is_an_event_with_its_issue_run_tool_and_input(world: World) -> None:
    batch_with_denials(world)

    denied = [
        {key: event.get(key) for key in ("issue", "run", "tool", "input")}
        for event in events(world)
        if event["event"] == "permission_denied"
    ]
    assert denied == [
        {"issue": 10, "run": "implementation", "tool": "Bash", "input": PUSH},
        {"issue": 10, "run": "implementation", "tool": "Bash", "input": LONG},
        {"issue": 10, "run": "review", "tool": "Write", "input": WRITE},
    ]


def test_the_summary_lists_each_denial_below_its_table(world: World) -> None:
    batch_with_denials(world)

    summary: str = world.gh()["issues"][str(BATCH)]["comments"][-1]
    lines = summary.splitlines()
    table_end = max(i for i, line in enumerate(lines) if line.startswith("| #"))
    below = lines[table_end + 1 :]
    assert "- #10 implementation: Bash `git push origin HEAD`" in below
    assert any(
        line.startswith("- #10 review: Write ") and "/project/marker.txt" in line for line in below
    )
    long_line = next(line for line in below if "echo xxx" in line)
    assert long_line.startswith("- #10 implementation: Bash `")
    assert LONG["command"][:200] in long_line
    assert LONG["command"][:201] not in long_line
