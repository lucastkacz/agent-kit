"""The review skill rates `high` what its checks say blocks (#74's review).

From the third review on, a new medium finding no longer blocks, so a finding that must block, such
as a change outside the issue, has to be rated `high`.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "review" / "SKILL.md"


def verdict() -> str:
    """The skill's Verdict section in lowercase, on one line."""
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## Verdict")
    end = text.find("\n## ", start + 1)
    return re.sub(r"\s+", " ", text[start : end if end != -1 else None]).lower()


def test_the_review_skill_rates_high_what_its_checks_say_blocks() -> None:
    section = verdict()
    for token in (
        "**`high`** is what a check above says blocks", "a change outside the issue",
        "acceptance tests changed or missing", "without a test that really checks it",
        "`make check` failing", "a security hole", "**`medium`** is the rest",
    ):  # fmt: skip
        assert token in section, (token, section)
