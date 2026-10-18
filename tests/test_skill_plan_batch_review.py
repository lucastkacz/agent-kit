"""The plan-batch skill covers what the review of #57 found missing."""

from __future__ import annotations

from test_skill_plan_batch import text


def section(number: int) -> str:
    """The skill's `## <number>.` section, up to the next one."""
    return text().split(f"\n## {number}. ", 1)[1].split("\n## ", 1)[0]


def test_a_blocked_issue_goes_in_only_once_the_owner_answers_its_question() -> None:
    start = section(1)
    assert "goes in only once the owner answers its question" in start
    assert "remove `blocked`" in start


def test_a_pending_acceptance_is_one_whose_run_has_ended() -> None:
    start = section(1)
    assert "whose run has ended" in start
    assert "`## Batch summary`" in start
    assert "running batch" in start


def test_it_lists_more_issues_than_gh_does_by_default() -> None:
    assert "--limit 200" in section(1)


def test_new_issues_are_labeled_with_their_type() -> None:
    assert "`task`, `bug`, `idea` or `spike`" in section(3)


def test_cloud_issues_are_in_no_lane() -> None:
    plan = section(4)
    assert "Cloud issues go only on that line, in no lane" in plan
    assert "no `Lane` or `Lanes:` lines" in plan


def test_it_reads_only_the_model_and_effort_keys_of_the_settings() -> None:
    plan = section(4)
    assert "Read only those two keys" in plan
    assert "never the whole file" in plan


def test_it_counts_the_batches_from_every_milestone() -> None:
    assert "milestones?state=all" in section(6)
