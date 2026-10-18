"""SPEC §3.3 says how acceptance closes a batch, and what a waiting high-risk PR changes (#59).

These check the facts only; whether the paragraph reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def acceptance() -> str:
    """SPEC §3.3 in lowercase, on one line, so that a check doesn't depend on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("### 3.3 Acceptance")
    end = text.index("\n### ", start + 1)
    return re.sub(r"\s+", " ", text[start:end]).lower()


def test_spec_3_3_says_acceptance_closes_the_tracking_issue_and_the_milestone() -> None:
    section = acceptance()
    assert "closes the tracking issue and the milestone" in section, section


def test_spec_3_3_says_a_waiting_high_risk_pr_keeps_the_batch_open_until_the_owner_asks() -> None:
    section = acceptance()
    for token in ("high-risk pr that hasn't merged", "item stays open", "asks to close the batch"):
        assert token in section, (token, section)
