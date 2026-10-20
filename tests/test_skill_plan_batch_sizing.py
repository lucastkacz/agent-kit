"""The plan-batch skill sizes a batch's issues so that each is worth its fixed cost (#135)."""

from __future__ import annotations

from plan_batch_skill import section
from spec_text import spec_section


def test_it_groups_issues_that_share_an_area_and_a_reason_before_proposing_lanes() -> None:
    start = section(1)
    assert "share an area and a reason" in start
    for area in (
        "the same file or function",
        "the same SPEC section",
        "the same skill",
        "the same root cause",
    ):
        assert area in start, f"step 1 doesn't group by {area!r}"
    assert "into one issue" in start
    assert "Before you propose lanes" in start


def test_it_keeps_unrelated_issues_apart_in_their_own_lanes() -> None:
    start = section(1)
    assert "Don't group unrelated issues just to have fewer" in start
    assert "separate lanes" in start


def test_it_gives_a_target_size_for_each_issue() -> None:
    start = section(1)
    assert "one to five acceptance criteria" in start
    assert "roughly 50 to 400 lines" in start
    assert "A smaller change joins an issue of the same area" in start
    assert "a larger one is split" in start
    assert "same size rules" in section(3)


def test_the_plan_names_each_merge_and_why_for_the_owners_approval() -> None:
    plan = section(4)
    assert "**Merges.**" in plan
    assert "each merge" in plan.lower()
    assert "why" in plan.split("**Merges.**", 1)[1].split("\n- ", 1)[0]
    setup = section(6)
    assert "with the criteria of each" in setup
    assert 'gh issue close <n> --reason "not planned" --comment' in setup


def test_the_spec_says_how_planning_sizes_issues() -> None:
    batches = spec_section("4.3 Batches")
    assert "Planning sizes the issues" in batches
    assert "share an area and a reason" in batches
    assert "one to five criteria" in batches
