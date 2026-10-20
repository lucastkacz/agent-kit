"""The routines' fork hands each issue's branch back, since Watch and the ship steps need it."""

from __future__ import annotations

from run_batch_skill import section, skill_text


def test_the_fork_reports_each_issues_branch_with_its_routine() -> None:
    send = section(skill_text(), "Send an issue to the cloud")
    report = send[send.index("reports only") :].split(":", 1)[0]
    assert "routine id" in report, report
    assert "`{branch}`" in report, report
