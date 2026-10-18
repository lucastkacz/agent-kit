"""Merging, the budget, the environment and the summary (small tests)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import budget, env, merge, report
from agent_batch.core.merge import MergeStatus
from agent_batch.core.model import IssueReport, Outcome, PrState
from agent_batch.core.plan import BatchPlan


def pr(state: str = "OPEN", mergeable: str = "MERGEABLE", *checks: str) -> PrState:
    return PrState(state, mergeable, "abc", checks)


def test_merge_states() -> None:
    assert merge.decide(pr("MERGED")) is MergeStatus.MERGED
    assert merge.decide(pr("CLOSED")) is MergeStatus.CLOSED
    assert merge.decide(pr("OPEN", "CONFLICTING")) is MergeStatus.CONFLICT
    assert merge.decide(pr("OPEN", "MERGEABLE", "SUCCESS", "FAILURE")) is MergeStatus.CHECKS_FAILED
    assert merge.decide(pr("OPEN", "UNKNOWN", "IN_PROGRESS", "SUCCESS")) is MergeStatus.WAIT


def test_the_command_line_budget_wins_over_the_plan() -> None:
    planned = BatchPlan(lanes=((1,),), max_issues=5, max_hours=2)
    assert budget.resolve(None, None, planned) == budget.Budget(5, 7200)
    assert budget.resolve(1, 0.5, planned) == budget.Budget(1, 1800)
    assert budget.resolve(None, None, BatchPlan(lanes=((1,),))) == budget.Budget()


@given(
    st.integers(min_value=0, max_value=50),
    st.integers(min_value=0, max_value=50),
    st.floats(min_value=0, max_value=1e6),
)
def test_a_budget_never_lets_more_issues_start_than_it_allows(
    limit: int, started: int, elapsed: float
) -> None:
    allowed = budget.allows(budget.Budget(max_issues=limit), started, elapsed)
    assert allowed is (started < limit)


def test_time_runs_out() -> None:
    hour = budget.Budget(max_seconds=3600)
    assert budget.allows(hour, 10, 3599) is True
    assert budget.allows(hour, 10, 3600) is False


@given(st.dictionaries(st.text(min_size=1), st.text()))
def test_the_clean_environment_has_no_api_keys_or_session_markers(original: dict[str, str]) -> None:
    original = {**original, "ANTHROPIC_API_KEY": "k", "CLAUDECODE": "1", "CLAUDE_CODE_X": "1"}
    cleaned = env.clean_env(original)
    assert not env.API_KEYS & cleaned.keys()
    assert "CLAUDECODE" not in cleaned
    assert not any(k.startswith("CLAUDE_CODE_") and k not in env.KEPT for k in cleaned)
    assert all(original[k] == v for k, v in cleaned.items())


def test_the_subscription_token_and_other_variables_stay() -> None:
    cleaned = env.clean_env({"CLAUDE_CODE_OAUTH_TOKEN": "t", "PATH": "/bin", "HOME": "/h"})
    assert cleaned == {"CLAUDE_CODE_OAUTH_TOKEN": "t", "PATH": "/bin", "HOME": "/h"}


def test_the_runs_do_not_inherit_the_virtual_environment() -> None:
    cleaned = env.clean_env(
        {"VIRTUAL_ENV": "/main/.venv", "CLAUDE_CODE_OAUTH_TOKEN": "t", "PATH": "/bin", "HOME": "/h"}
    )
    assert cleaned == {"CLAUDE_CODE_OAUTH_TOKEN": "t", "PATH": "/bin", "HOME": "/h"}


@given(st.dictionaries(st.text(min_size=1), st.text()))
def test_dropping_the_virtual_environment_keeps_every_other_variable(
    original: dict[str, str],
) -> None:
    without = {k: v for k, v in original.items() if k != "VIRTUAL_ENV"}
    assert env.clean_env({**original, "VIRTUAL_ENV": "/main/.venv"}) == env.clean_env(without)


def test_the_summary_counts_and_lists_what_needs_the_owner() -> None:
    reports = [
        IssueReport(11, Outcome.MERGED, pr=21, review_rounds=1, seconds=600, human_checks=1),
        IssueReport(12, Outcome.WAITING_OWNER, "the issue is marked high risk", pr=22),
        IssueReport(13, Outcome.BLOCKED, "Which currency?\nMore text.", denials=2, cost_usd=0.5),
        IssueReport(14, Outcome.DEFERRED, "#13 didn't merge"),
    ]
    text = report.render(reports, 1800)
    assert "| #11 | merged | #21 | 1 | 0 | 10 |" in text
    assert "merged 1 · waiting for the owner 1 · blocked 1 · deferred 1" in text
    assert "**Human checks:** 1" in text
    assert "**Permission denials:** 2" in text
    assert "**Time:** 30 min" in text
    assert "- #22: waiting for the owner. the issue is marked high risk." in text
    assert "- #13: blocked. Which currency?" in text
    assert "#14:" not in text
