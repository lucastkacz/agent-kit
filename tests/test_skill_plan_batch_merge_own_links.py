"""Planning's merges leave the links within a merge, and keep its not-planned blockers (#172)."""

from __future__ import annotations

from plan_batch_skill import merge_step, section


def test_a_merge_skips_the_links_between_its_own_issues() -> None:
    merge = merge_step()
    assert "Links within the merge don't move" in merge
    assert "skip any `<b>` or `<a>` that is `<m>` or another issue of the same merge" in merge
    assert "so that `<m>` never waits for itself" in merge


def test_a_merge_moves_the_blockers_closed_as_not_planned_too() -> None:
    merge = merge_step()
    assert "So does each of its blockers closed as not planned" in merge
    assert "one merged into another issue moves as that issue" in merge


def test_the_dependencies_rule_names_how_to_read_a_blockers_merge_comment() -> None:
    plan = section(4)
    assert "`gh issue view <m> --json stateReason,comments`" in plan
