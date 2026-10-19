"""The plan-batch skill orders a batch by GitHub's native "blocked by" links (#121)."""

from __future__ import annotations

from pathlib import Path

from test_skill_plan_batch_rules import section

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def test_it_reads_each_candidates_blocked_by_links() -> None:
    start = section(1)
    assert "gh issue view <n> --json blockedBy" in start


def test_it_plans_an_issue_only_after_its_open_low_risk_blockers_in_the_same_lane() -> None:
    plan = section(4)
    assert "**Dependencies.**" in plan
    assert "after each of its open blockers, in the same lane" in plan
    assert "only when those blockers are low risk" in plan
    assert "waits for a later batch, and the plan says why" in plan


def test_it_links_a_new_issue_to_the_issues_it_needs() -> None:
    writing = section(3)
    assert "gh issue edit <n> --add-blocked-by <m>" in writing


def test_the_spec_records_a_dependency_as_a_blocked_by_link_and_keeps_lanes_on_files() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    assert 'A dependency is recorded as a GitHub "blocked by" link' in spec
    assert "lanes still follow the files the issues touch, for conflicts" in spec
