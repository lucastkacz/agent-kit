"""The `accept-batch` skill prices each runner's stretch of a resumed batch's log (#217)."""

from __future__ import annotations

from accept_batch_skill import section


def notional_cost() -> str:
    walk = section("Walk the owner through")
    numbers = walk[walk.index("### 2.6") :]
    return numbers[numbers.index("the notional cost") :]


def test_a_stretch_logged_before_run_ended_takes_its_runners_summary_instead() -> None:
    text = notional_cost()
    for token in ("`batch_started`", "stretch", "without `run_ended` events", "summary"):
        assert token in text, (token, text)
