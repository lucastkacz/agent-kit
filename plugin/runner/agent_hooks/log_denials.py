"""A PermissionDenied hook: each denial goes to a log that acceptance reviews (SPEC §10.1).

Claude Code fires it when auto mode denies a call; deny rules and other hooks don't fire it.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from agent_hooks.repo import main_root

INPUT_KEYS = ("command", "file_path", "url", "pattern")
MAX_INPUT = 300


def main() -> int:
    payload = json.load(sys.stdin)
    root = main_root(Path(payload.get("cwd") or "."))
    if root is None:
        return 0
    entry = {
        "time": datetime.now(UTC).isoformat(timespec="seconds"),
        "session": payload.get("session_id"),
        "tool": payload.get("tool_name"),
        "input": _summary(payload.get("tool_input")),
        "reason": payload.get("reason"),
    }
    log = root / ".agent-batch" / "denials.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as out:
        out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return 0


def _summary(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in INPUT_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str):
            return value[:MAX_INPUT]
    return json.dumps(tool_input, ensure_ascii=False)[:MAX_INPUT]
