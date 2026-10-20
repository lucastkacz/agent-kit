"""What tests of the follow-up issue that a PR's found work opens share."""

from __future__ import annotations

import json
from typing import Any

from batch_runs import BATCH
from conftest import World
from review_rounds import finding

DATES = {"kind": "idea", "title": "Dates drift", "body": "Seen in the importer."}
TRIMS = finding("medium", "new", "d.py:5", "It trims the trailing spaces of every line.")
CONFLICT = {"file": "shared.txt", "content": "another lane\n"}
CONFLICTING = {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": CONFLICT}


def follow_ups(world: World) -> list[dict[str, Any]]:
    """The issues the runner opened, beyond the one worked on and its batch."""
    return [i for n, i in world.gh()["issues"].items() if n not in (str(BATCH), "10")]


def issue_found(world: World) -> list[dict[str, Any]]:
    """The `issue_found` events in every log of the project."""
    logs = sorted((world.project / ".agent-batch").glob("*/events.jsonl"))
    records = [json.loads(line) for log in logs for line in log.read_text().splitlines()]
    return [record for record in records if record["event"] == "issue_found"]
