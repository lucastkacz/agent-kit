"""The `accept-batch` skill counts each run's cost once, from the event logs (#217)."""

from __future__ import annotations

from accept_batch_skill import section


def notional_cost() -> str:
    """Step 2.6's paragraph on the notional cost."""
    walk = section("Walk the owner through")
    numbers = walk[walk.index("### 2.6") :]
    return numbers[numbers.index("the notional cost") :]


def has(text: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, (missing, text)


def test_it_sums_each_run_ended_and_reviewed_events_cost_in_the_batchs_log() -> None:
    has(
        notional_cost(),
        "`run_ended`",
        "`reviewed`",
        "`cost_usd`",
        ".agent-batch/batch-<n>/events.jsonl",
        "once",
    )


def test_it_doesnt_add_the_summarys_notional_cost_to_the_runs_it_already_counts() -> None:
    has(notional_cost(), "don't add the runner's summary")
