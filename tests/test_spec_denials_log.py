"""SPEC §10.1 says what `.agent-batch/denials.jsonl` holds, protect-master's blocks included (#87).

These check the facts only; whether the paragraph reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def zero_prompts() -> str:
    """SPEC §10.1 in lowercase, on one line, so that a check doesn't depend on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("### 10.1 Zero prompts during a batch")
    end = text.index("\n### ", start + 1)
    return re.sub(r"\s+", " ", text[start:end]).lower()


def test_spec_10_1_says_protect_master_logs_its_blocks_from_any_session() -> None:
    section = zero_prompts()
    for token in (
        "protect-master",
        "each command it blocks",
        "`.agent-batch/denials.jsonl`",
        "any session",
        "interactive sessions",
        "lanes",
        "reviews",
    ):
        assert token in section, (token, section)
