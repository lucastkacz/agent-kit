"""Acceptance tests for #41: the `Budget:` issue count (small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import plan
from agent_batch.core.plan import PlanError


def test_a_decimal_issue_count_fails_quoting_what_the_owner_wrote() -> None:
    with pytest.raises(PlanError, match=r"`Budget:`.*'1\.0 issues'"):
        plan.parse_plan("Lane 1: #1\nBudget: 1.0 issues\n")


def test_a_budget_of_ten_issues_and_two_hours_reads_both() -> None:
    parsed = plan.parse_plan("Lane 1: #1\nBudget: 10 issues, 2 hours\n")
    assert (parsed.max_issues, parsed.max_hours) == (10, 2.0)
