"""run-batch writes a cloud branch's title again when `ship` refuses it, and ships again (#236)."""

from __future__ import annotations

from run_batch_skill import section, skill_text, step


def test_a_refused_cloud_title_is_written_from_the_issues_title_and_shipped_again() -> None:
    ship = step(section(skill_text(), "Bring a cloud branch back"), 5)
    assert "refuses the title" in ship, ship
    assert "before any review" in ship, ship
    assert "Conventional Commits title of at most 72 characters" in ship, ship
    assert "from the issue's title" in ship, ship
    assert "ship again" in ship, ship
