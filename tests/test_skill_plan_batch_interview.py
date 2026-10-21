"""plan-batch interviews the owner about every issue it will label `ready` (#253)."""

from __future__ import annotations

from plan_batch_skill import section


def test_a_new_idea_is_settled_with_the_interview_skill() -> None:
    assert "the `interview` skill" in section(2)


def test_it_calls_the_interview_for_every_issue_it_will_label_ready() -> None:
    write = section(3)
    assert "with the `interview` skill" in write
    assert "each issue the batch will label `ready`" in write
    assert "not the `ready` issues an earlier batch left behind" in write


def test_the_plan_shows_each_issues_ready_check() -> None:
    plan = section(4)
    assert "**Ready check.**" in plan
    assert "Each issue's ready check" in plan


def test_the_ready_check_comes_before_the_one_approval() -> None:
    approval = section(5)
    assert "after each issue's ready check" in approval
    assert approval.index("One approval") < approval.index("after each issue's ready check")
