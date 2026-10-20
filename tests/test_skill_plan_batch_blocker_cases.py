"""The plan-batch skill says when a blocker is done, and what a cloud blocker means (#121)."""

from __future__ import annotations

from plan_batch_skill import section


def test_a_blocker_counts_as_done_only_when_its_closed_as_completed() -> None:
    plan = section(4)
    assert "A blocker counts as done only when it's closed as completed" in plan
    assert "`gh issue view <m> --json stateReason` says `COMPLETED`" in plan
    assert "One closed as not planned never landed its code, so it still blocks." in plan
    assert "An issue whose blockers are all done plans as usual." in plan


def test_an_issue_whose_blocker_goes_to_the_cloud_waits_for_a_later_batch() -> None:
    plan = section(4)
    assert "So does an issue whose blocker goes to the cloud" in plan
    assert "a `Cloud:` issue is in no lane, so nothing can follow it in one" in plan
