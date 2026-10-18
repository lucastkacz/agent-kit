"""Helpers for the contract tests, which run the real `claude` and `gh`."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
RECORDED = Path(__file__).parent / "recorded"


def record(name: str, raw: str) -> None:
    """Keeps a real answer, so that `make check` can compare the fakes with it."""
    RECORDED.mkdir(exist_ok=True)
    pretty = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    (RECORDED / f"{name}.json").write_text(pretty + "\n", encoding="utf-8")


def unique(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC):%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
