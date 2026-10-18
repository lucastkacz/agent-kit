"""Risk, eligibility and the batch plan (small tests)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import eligibility, plan, risk
from agent_batch.core.model import Issue
from agent_batch.core.plan import PlanError


def issue(body: str = "### Risk\n\nLow\n", labels: tuple[str, ...] = ("ready",)) -> Issue:
    return Issue(7, "A task", body, "owner", frozenset(labels), "OPEN")


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("### Risk\n\nLow — only a label.\n", False),
        ("### Risk\n\nHigh: it writes the database.\n", True),
        ("### Goal\n\nx\n\n### risk\n\n\nhigh\n", True),
        ("### Risk\n\n### Why\n\nlow\n", None),
        ("### Risk\n\nMedium\n", None),
        ("No risk section.", None),
        ("### Risk\n", None),
    ],
)
def test_the_stated_risk_comes_from_the_risk_section(body: str, expected: bool | None) -> None:
    assert risk.stated_risk(body) is expected


def test_a_low_risk_issue_with_ordinary_files_is_low() -> None:
    level = risk.classify(["src/app.py", "tests/test_app.py"], [], issue())
    assert level.high is False
    assert level.reasons == ()


def test_each_reason_for_high_risk_is_listed() -> None:
    marked = issue("### Risk\n\nHigh\n", labels=("ready", "risk:high"))
    level = risk.classify(["uv.lock", "src/money.py"], ["src/money.py"], marked)
    assert level.high is True
    assert level.reasons == (
        "the issue is marked high risk",
        "the issue is labeled risk:high",
        "`uv.lock` matches `uv.lock`",
        "`src/money.py` matches `src/money.py`",
    )


def test_an_issue_without_a_stated_risk_is_high() -> None:
    assert risk.classify([], [], issue("Nothing.")).high is True


def test_risk_paths_skip_blanks_and_comments() -> None:
    text = "# Money\nsrc/money/\n\n  src/tax.py  \n"
    assert risk.parse_patterns(text) == ("src/money/", "src/tax.py")


def test_human_checks_are_counted() -> None:
    body = "- [ ] a. Verify: human(taste)\n- [ ] b. Verify: unit\n- [ ] c. Verify: human(hardware)"
    assert risk.count_human_checks(body) == 2


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"state": "CLOSED"}, "the issue is closed"),
        ({"author": "stranger"}, "it was opened by stranger, not by the owner"),
        ({"labels": frozenset()}, "it isn't labeled ready"),
        ({"labels": frozenset({"ready", "blocked"})}, "it's labeled blocked"),
        ({"body": "No risk."}, "it doesn't state its risk"),
    ],
)
def test_issues_agents_may_not_take(changes: dict[str, object], reason: str) -> None:
    fields: dict[str, object] = {
        "number": 7,
        "title": "t",
        "body": "### Risk\n\nLow\n",
        "author": "owner",
        "labels": frozenset({"ready"}),
        "state": "OPEN",
    }
    candidate = Issue(**{**fields, **changes})  # type: ignore[arg-type]
    assert eligibility.refusal(candidate, "owner") == reason


def test_a_ready_issue_of_the_owner_can_be_taken() -> None:
    assert eligibility.refusal(issue(), "owner") is None


def test_a_plan_has_lanes_and_an_optional_budget() -> None:
    body = "Some text.\n\nLane 1: #12, #15\n  lane 2 : #13 (UI)\nBudget: 4 issues, 2.5 hours\n"
    parsed = plan.parse_plan(body)
    assert parsed.lanes == ((12, 15), (13,))
    assert parsed.max_issues == 4
    assert parsed.max_hours == 2.5


def test_a_budget_can_give_only_hours() -> None:
    parsed = plan.parse_plan("Lane 1: #1\nBudget: 3h\n")
    assert (parsed.max_issues, parsed.max_hours) == (None, 3.0)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("No lanes here.", "no lane plan"),
        ("Lane 1: nothing\n", "no lane plan"),
        ("Lane 1: #1, #2\nLane 2: #2\n", "more than one lane: #2"),
    ],
)
def test_plans_that_cant_run(body: str, message: str) -> None:
    with pytest.raises(PlanError, match=message):
        plan.parse_plan(body)


@given(
    st.lists(
        st.lists(st.integers(min_value=1, max_value=99_999), min_size=1, max_size=5),
        min_size=1,
        max_size=4,
    ).filter(lambda lanes: len({n for lane in lanes for n in lane}) == sum(map(len, lanes)))
)
def test_a_formatted_plan_parses_back_to_its_lanes(lanes: list[list[int]]) -> None:
    parsed = plan.parse_plan(plan.format_lanes(lanes))
    assert parsed.lanes == tuple(tuple(lane) for lane in lanes)


def test_a_budget_of_zero_issues_cant_run() -> None:
    with pytest.raises(PlanError, match=r"`Budget:`.*'0 issues'"):
        plan.parse_plan("Lane 1: #1\nBudget: 0 issues, 2 hours\n")


@pytest.mark.parametrize("hours", ["0 hours", "0h", "0.0 hours"])
def test_a_budget_of_zero_hours_cant_run(hours: str) -> None:
    with pytest.raises(PlanError, match=rf"`Budget:`.*'{hours}'"):
        plan.parse_plan(f"Lane 1: #1\nBudget: 3 issues, {hours}\n")


def test_a_budget_of_issues_and_hours_reads_both() -> None:
    parsed = plan.parse_plan("Lane 1: #1\nBudget: 3 issues, 2.5 hours\n")
    assert (parsed.max_issues, parsed.max_hours) == (3, 2.5)
