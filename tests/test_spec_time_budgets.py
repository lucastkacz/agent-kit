"""SPEC §7.3 says how a time budget is measured, and what its evidence gives (#165).

These check the facts only; whether the paragraph reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def time_budgets() -> str:
    """SPEC §7.3's time budgets in lowercase, on one line, so that no check depends on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    section = text.index("### 7.3 Fast and proportionate checks")
    start = text.index("- **Time budgets.**", section)
    end = text.index("\n- **", start + 1)
    return re.sub(r"\s+", " ", text[start:end]).lower()


def test_spec_7_3_measures_the_budgets_with_no_batch_running() -> None:
    assert "no batch running" in time_budgets()


def test_spec_7_3_has_a_times_evidence_give_the_load_average_beside_it() -> None:
    section = time_budgets()
    for token in ("evidence", "load average"):
        assert token in section, (token, section)
