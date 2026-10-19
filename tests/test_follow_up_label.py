"""A PR's follow-up issue takes the most severe kind among its items as its label (#136)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import followup
from agent_batch.core.model import FoundIssue, IssueKind

KINDS: tuple[IssueKind, ...] = ("bug", "task", "idea")


def item(kind: IssueKind) -> FoundIssue:
    return FoundIssue(kind, f"A {kind}", f"The {kind}'s body.")


def test_the_follow_up_is_a_bug_when_any_item_is_a_bug() -> None:
    assert followup.label([item("idea"), item("bug"), item("task")]) == "bug"


def test_the_follow_up_is_a_task_when_no_item_is_a_bug_and_any_is_a_task() -> None:
    assert followup.label([item("idea"), item("task"), item("idea")]) == "task"


def test_the_follow_up_is_an_idea_when_every_item_is_an_idea() -> None:
    assert followup.label([item("idea"), item("idea")]) == "idea"


@given(st.lists(st.sampled_from(KINDS), min_size=1))
def test_the_follow_up_takes_the_most_severe_kind_among_its_items(kinds: list[IssueKind]) -> None:
    expected = next(kind for kind in KINDS if kind in kinds)

    assert followup.label([item(kind) for kind in kinds]) == expected
