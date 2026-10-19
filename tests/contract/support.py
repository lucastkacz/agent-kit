"""Helpers for the contract tests, which run the real `claude` and `gh`."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from agent_batch.shell import proc

KIT = Path(__file__).resolve().parents[2]
RECORDED = Path(__file__).parent / "recorded"


def record(name: str, raw: str) -> None:
    """Keeps a real answer, so that `make check` can compare the fakes with it."""
    RECORDED.mkdir(exist_ok=True)
    pretty = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    (RECORDED / f"{name}.json").write_text(pretty + "\n", encoding="utf-8")


def record_stream(name: str, raw: str) -> None:
    """Keeps the messages of a real stream that the runner reads: the assistant's and the result.

    The others, such as the start's list of plugins and connectors, describe the owner's computer.
    """
    messages = [json.loads(line) for line in raw.splitlines() if line.strip()]
    kept = [message for message in messages if message.get("type") in ("assistant", "result")]
    record(name, json.dumps(kept))


def make_project(folder: Path) -> Path:
    """A git repository with one commit, for a run to work in."""
    proc.must(["git", "init", "--quiet", "-b", "master"], folder)
    (folder / "README.md").write_text("A contract test's project.\n")
    proc.must(["git", "add", "-A"], folder)
    proc.must(["git", "commit", "--quiet", "-m", "chore: start"], folder)
    return folder


def unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC):%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
