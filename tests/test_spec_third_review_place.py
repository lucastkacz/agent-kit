"""SPEC §5, step 5 says where a branch's third review happens (#113).

A batch blocks an issue after two rounds without approval, so the rule for the third review acts
on a later one. This checks the facts only; whether the wording reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def review_step() -> str:
    """SPEC §5, step 5, in lowercase on one line."""
    text = SPEC.read_text(encoding="utf-8")
    section = text[text.index("## 5. The issue pipeline") : text.index("## 6. Contexts")]
    step = next(line for line in section.splitlines() if line.startswith("5. **Review.**"))
    return re.sub(r"\s+", " ", step).lower()


def test_spec_5_says_a_branchs_third_review_comes_after_the_batch_blocks_the_issue() -> None:
    step = review_step()
    for token in (
        "after two rounds without approval", "third review", "`agent-batch ship`",
        "unblocks", "event log",
    ):  # fmt: skip
        assert token in step, (token, step)
