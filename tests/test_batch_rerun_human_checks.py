"""A re-run's summary still counts the human checks of the issues that merged before (#66)."""

from __future__ import annotations

from conftest import World
from test_batch_rerun import BATCH, stop_after_the_first_issue, summary


def test_a_rerun_summary_counts_the_human_checks_of_an_issue_that_merged_before(
    world: World,
) -> None:
    stop_after_the_first_issue(world)

    world.run("run", str(BATCH))

    # Each issue asks for one human check; the owner still makes #10's at the acceptance.
    assert "**Human checks:** 2" in summary(world)
