"""SPEC §5, step 5 describes the low pass of an approved review's findings (#252)."""

from __future__ import annotations

from spec_text import SPEC, flat


def test_spec_5_review_step_describes_the_low_pass() -> None:
    step = flat(SPEC.read_text(encoding="utf-8"), "5. **Review.**", "\n6. **Pull request.**")
    for token in (
        "low pass", "approves a branch with low findings", "once per branch",
        "reviews the branch again", "doesn't count", "`low_pass`",
    ):  # fmt: skip
        assert token in step, (token, step)
