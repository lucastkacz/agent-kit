"""SPEC §10.1 says what `.agent-batch/denials.jsonl` holds, protect-master's blocks included (#87).

These check the facts only; whether the paragraph reads well stays the owner's call.
"""

from __future__ import annotations

from spec_text import zero_prompts


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
