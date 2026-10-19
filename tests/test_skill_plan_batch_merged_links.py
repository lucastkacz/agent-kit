"""Planning's merges move the merged issue's links (#172).

And an issue whose blocker was closed as not planned goes to the owner.
"""

from __future__ import annotations

from test_skill_plan_batch_rules import section


def merge_step() -> str:
    """Step 6.1 of the skill: the merges."""
    return section(6).split("\n1. ", 1)[1].split("\n2. ", 1)[0]


def test_a_merge_moves_the_merged_issues_links_to_the_issue_that_holds_it_before_closing_it() -> (
    None
):
    merge = merge_step()
    assert "gh issue view <n> --json blockedBy,blocking" in merge
    assert "gh issue edit <b> --add-blocked-by <m> --remove-blocked-by <n>" in merge
    assert "gh issue edit <m> --add-blocked-by <a>" in merge
    assert "each of its open blockers `<a>`" in merge
    assert merge.index("--add-blocked-by <m>") < merge.index(
        'gh issue close <n> --reason "not planned"'
    )


def test_a_blocker_merged_into_another_issue_counts_through_that_issue() -> None:
    plan = section(4)
    assert (
        'A blocker closed as not planned with the comment "Merged into #<h>." counts through #<h>'
        in plan
    )


def test_an_issue_whose_blocker_was_closed_as_not_planned_goes_to_the_owner() -> None:
    plan = section(4)
    assert (
        "An issue whose blocker was closed as not planned, and not merged into another, "
        "goes to the owner" in plan
    )
    assert "remove the link, rewrite the issue or close it" in plan
    assert "instead of waiting for a later batch" in plan
