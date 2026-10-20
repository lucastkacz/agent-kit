"""A merged issue takes the highest risk of the issues it joins (#135, review round 1)."""

from __future__ import annotations

from plan_batch_skill import section


def test_a_merged_issue_takes_the_highest_risk_of_the_issues_it_joins() -> None:
    setup = section(6)
    assert "Its `### Risk` is the highest of the merged issues'" in setup
    assert "one high-risk issue makes the merge high risk" in setup
    assert "SPEC §9.2" in setup
