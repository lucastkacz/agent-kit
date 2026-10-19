"""run-batch ships only a `done` run's PR commit, and keeps its trailers out of the PR."""

from __future__ import annotations

from test_skill_run_batch_cloud_dispatch import section, skill_text


def test_the_runs_status_is_read_before_its_branch_is_brought_back() -> None:
    back = section(skill_text(), "Bring a cloud branch back")
    first = back.split("\n\n")[1]
    assert "first read their reports" in first, first
    assert "only a run that answered `done`" in first, first
    assert "its PR commit as its branch's head" in first, first
    status = back.index("reports only each run's status")
    assert status < back.index("give them to a general-purpose subagent"), back
    assert status < back.index("\n1. "), back
