"""SPEC §12.1 and §11.5 cover a cloud issue's `make e2e` and the batch's one-time routines (#77).

These check the facts only; whether the wording reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPEC.md"
RUN_BATCH = ROOT / "plugin" / "skills" / "run-batch" / "SKILL.md"


def flat(text: str, start_marker: str, end_marker: str) -> str:
    """The text from one marker to the next, lowercase and on one line, whatever the wrapping."""
    start = text.index(start_marker)
    end = text.find(end_marker, start + 1)
    return re.sub(r"\s+", " ", text[start : end if end != -1 else len(text)]).lower()


def spec_section(heading: str) -> str:
    return flat(SPEC.read_text(encoding="utf-8"), f"### {heading}", "\n#")


def bring_back() -> str:
    return flat(RUN_BATCH.read_text(encoding="utf-8"), "## Bring a cloud branch back", "\n## ")


def test_spec_12_1_runs_make_e2e_for_e2e_criteria_before_ship() -> None:
    section = spec_section("12.1 Back to the merge gate")
    assert "runs `make e2e` in the worktree" in section, section
    assert "verified by `e2e`" in section, section
    e2e = section.index("`make e2e`")
    ship = section.index("`agent-batch ship <issue>`")
    assert e2e < ship, section
    assert "before `agent-batch ship" in section, section


def test_spec_12_1_refers_to_direct_mode_as_3_4() -> None:
    section = spec_section("12.1 Back to the merge gate")
    assert "direct mode (§3.4)" in section, section
    assert "direct mode (§3)" not in section, section


def test_run_batch_runs_make_e2e_in_the_worktree_before_ship() -> None:
    section = bring_back()
    assert "verified by `e2e`" in section, section
    assert "run `make e2e`" in section, section
    assert section.index("`make e2e`") < section.index("`agent-batch ship <n>"), section


def test_spec_11_5_says_cloud_issues_go_out_as_one_time_routines_when_the_batch_starts() -> None:
    section = spec_section("11.5 Nothing starts by itself")
    assert "one-time routines" in section, section
    assert "when the owner starts the batch" in section, section
    assert "cloud issues" in section, section
