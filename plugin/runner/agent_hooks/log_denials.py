"""A PermissionDenied hook: each denial goes to a log that acceptance reviews (SPEC §10.1).

Claude Code fires it when auto mode denies a call; deny rules and other hooks don't fire it, so
protect-master writes its own blocks to the same log.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_hooks.repo import project_root

INPUT_KEYS = ("command", "file_path", "url", "pattern")
MAX_INPUT = 300


def main() -> int:
    payload = json.load(sys.stdin)
    root = project_root(Path(payload.get("cwd") or "."))
    if root is None:
        return 0
    append(root, entry(payload, payload.get("reason"), datetime.now(UTC)))
    return 0


def entry(payload: dict[str, Any], reason: object, now: datetime) -> dict[str, object]:
    """The log's line for a hook event's denied call."""
    return {
        "time": now.isoformat(timespec="seconds"),
        "session": payload.get("session_id"),
        "tool": payload.get("tool_name"),
        "input": _summary(payload.get("tool_input")),
        "reason": reason,
    }


def append(root: Path, line: dict[str, object]) -> None:
    log = root / ".agent-batch" / "denials.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as out:
        out.write(json.dumps(line, ensure_ascii=False) + "\n")


def _summary(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in INPUT_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str):
            return value[:MAX_INPUT]
    return json.dumps(tool_input, ensure_ascii=False)[:MAX_INPUT]
