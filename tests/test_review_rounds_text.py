"""The review skill and SPEC §5 and §6 say how a re-review works (#74).

These check the facts only; whether the SPEC's wording reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPEC.md"
SKILL = ROOT / "plugin" / "skills" / "review" / "SKILL.md"


def flat(text: str) -> str:
    """The text in lowercase, on one line, so that a check doesn't depend on wrapping."""
    return re.sub(r"\s+", " ", text).lower()


def spec_section(heading: str, following: str) -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(heading)
    return flat(text[start : text.index(following, start)])


def test_the_review_skill_says_how_a_re_review_treats_the_earlier_findings_and_new_ones() -> None:
    text = flat(SKILL.read_text(encoding="utf-8"))
    for token in (
        "re-review", "earlier rounds' findings", "fixed or answered", "`earlier`",
        "`regression`", "`new`", "from the third review", "filed as an issue", "still blocks",
    ):  # fmt: skip
        assert token in text, (token, text)


def test_spec_5_says_how_a_re_review_treats_the_earlier_findings_and_new_ones() -> None:
    section = spec_section("## 5. The issue pipeline", "## 6. Contexts")
    for token in (
        "re-review", "earlier rounds' findings", "fixed or answered", "third review",
        "new medium finding", "regression", "(§4.5)", "still blocks",
    ):  # fmt: skip
        assert token in section, (token, section)


def test_spec_6_says_a_re_review_gets_the_earlier_rounds_findings() -> None:
    section = spec_section("## 6. Contexts", "## 7. Verification")
    for token in ("re-review", "earlier rounds' findings"):
        assert token in section, (token, section)
