"""SPEC §4.5 says that a PR's found work goes in one follow-up issue (#136).

This checks the facts only; whether the wording reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def found_work_section() -> str:
    """SPEC §4.5, in lowercase on one line."""
    text = SPEC.read_text(encoding="utf-8")
    section = text[text.index("### 4.5 Work found along the way") : text.index("## 5. ")]
    return re.sub(r"\s+", " ", section).lower()


def test_spec_4_5_says_a_prs_found_work_goes_in_one_follow_up_issue() -> None:
    section = found_work_section()
    for token in ("one follow-up issue", "found while working on #n", "without `ready`"):
        assert token in section, (token, section)
