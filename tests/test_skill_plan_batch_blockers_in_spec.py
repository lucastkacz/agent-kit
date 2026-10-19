"""SPEC §4.3 and plan-batch's Dependencies rule say the same about blockers (#191).

And the rule gives the blocker and the issue that holds its merge names of their own.
"""

from __future__ import annotations

import re

from test_skill_plan_batch_rules import section, spec_section


def dependencies_rule() -> str:
    """Step 4's **Dependencies** rule, up to the next bullet."""
    return section(4).split("- **Dependencies.**", 1)[1].split("\n- ", 1)[0]


def placeholders(pattern: str, rule: str) -> set[str]:
    """The placeholders that fill `<...>` in each match of `pattern`."""
    return set(re.findall(pattern, rule))


def test_the_spec_says_a_blocker_merged_into_another_issue_counts_through_that_issue() -> None:
    spec = spec_section("4.3 Batches")
    assert "merged into another issue counts through that issue" in spec


def test_the_spec_sends_an_issue_whose_blocker_was_closed_as_not_planned_to_the_owner() -> None:
    spec = spec_section("4.3 Batches")
    assert (
        "An issue whose blocker was closed as not planned, and not merged into another, "
        "goes to the owner" in spec
    )


def test_the_dependencies_rule_names_the_blocker_and_the_issue_that_holds_its_merge_apart() -> None:
    rule = dependencies_rule()
    blocker = placeholders(r"gh issue view <(\w+)> --json stateReason,comments", rule)
    holder = placeholders(r'"Merged into #<(\w+)>\."', rule)
    holder |= placeholders(r"counts through #<(\w+)>", rule)
    holder |= placeholders(r"done when #<(\w+)> is", rule)
    holder |= placeholders(r"as if #<(\w+)> blocked it", rule)
    assert len(blocker) == 1
    assert len(holder) == 1
    assert blocker != holder
