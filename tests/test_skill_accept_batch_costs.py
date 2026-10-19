"""The `accept-batch` skill counts the local reviews' cost in a batch's notional cost (#76)."""

from __future__ import annotations

from test_skill_accept_batch import section


def numbers() -> str:
    """Step 2.6, the batch's numbers."""
    walk = section("Walk the owner through")
    return walk[walk.index("### 2.6") :]


def has(text: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, (missing, text)


def test_it_adds_each_issues_ship_review_costs_to_the_notional_cost() -> None:
    has(
        numbers(), "notional cost", "`reviewed`", "`cost_usd`", ".agent-batch/ship-<i>/events.jsonl"
    )


def test_it_says_the_cloud_runs_cost_isnt_known() -> None:
    has(numbers(), "cloud", "cost isn't known")
