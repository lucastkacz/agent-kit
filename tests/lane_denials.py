"""What tests of a lane's permission denials share: a denial, its logs, a batch with some."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from batch_runs import BATCH
from conftest import World

SESSION = "session-implement-10-0"
CHECK = {"command": 'make check > /tmp/lane2-check-54.log 2>&1; echo "exit $?"'}


def denial(tool: str, tool_input: dict[str, Any], **extra: str) -> dict[str, Any]:
    return {"tool_name": tool, "tool_use_id": "t1", "tool_input": tool_input, **extra}


def denials_log(world: World) -> Path:
    return world.project / ".agent-batch" / "denials.jsonl"


def run_batch(world: World, implement: dict[str, Any]) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    world.script("implement", 10, implement)
    world.run("run", str(BATCH))


def events(world: World) -> list[dict[str, Any]]:
    log = world.project / ".agent-batch" / f"batch-{BATCH}" / "events.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    return [record for record in records if record["event"] == "permission_denied"]
