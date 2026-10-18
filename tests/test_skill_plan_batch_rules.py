"""The plan-batch skill's rules for blocked, deferred and cloud issues, labels and batch numbers.

Also that the SPEC says what planning proposes, and that its batch example runs every lane at once.
"""

from __future__ import annotations

from pathlib import Path

from agent_batch.core.plan import parse_plan
from test_skill_plan_batch import text

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def section(number: int) -> str:
    """The skill's `## <number>.` section, up to the next one."""
    return text().split(f"\n## {number}. ", 1)[1].split("\n## ", 1)[0]


def spec_section(heading: str) -> str:
    """The SPEC's `### <heading>` section, up to the next heading."""
    return SPEC.read_text(encoding="utf-8").split(f"\n### {heading}\n", 1)[1].split("\n#", 1)[0]


def test_a_blocked_issue_goes_in_only_once_the_owner_answers_its_question() -> None:
    start = section(1)
    assert "goes in only once the owner answers its question" in start
    assert "remove `blocked`" in start


def test_a_batchs_run_ends_when_each_issue_of_its_plan_is_done_with() -> None:
    start = section(1)
    assert "in its lanes and on its `Cloud:` line alike" in start
    assert "is closed, labeled `blocked`, has an open PR, or is `deferred`" in start


def test_a_pending_acceptance_is_an_ended_run_without_an_accepted_comment() -> None:
    start = section(1)
    assert 'its run has ended, and its tracking issue has no "Accepted." comment' in start
    assert "A batch whose run hasn't ended is running, or not started yet" in start


def test_it_proposes_first_the_ready_issues_an_earlier_batch_left_behind() -> None:
    start = section(1)
    assert "open `ready` issues an earlier batch left behind" in start
    assert "in a milestone whose batch has ended" in start
    assert "Propose them first" in start
    assert start.index("left behind") < start.index("Propose which issues go in")


def test_it_lists_more_issues_than_gh_does_by_default() -> None:
    assert "--limit 200" in section(1)


def test_each_new_issue_has_the_fields_of_its_types_form() -> None:
    assert "the fields of its type's form in SPEC §4.1" in section(3)


def test_new_issues_are_labeled_with_their_type() -> None:
    assert "`task`, `bug`, `idea` or `spike`" in section(3)


def test_risk_wins_over_sharing_a_lane() -> None:
    assert "risk wins: a second high-risk issue on the same files goes alone" in section(4)


def test_cloud_issues_are_in_no_lane() -> None:
    plan = section(4)
    assert "Cloud issues go only on that line, in no lane" in plan
    assert "no `Lane` or `Lanes:` lines" in plan


def test_it_reads_only_the_model_and_effort_keys_of_the_settings() -> None:
    plan = section(4)
    assert "Read only those two keys" in plan
    assert "never the whole file" in plan


def test_a_missing_setting_is_asked_with_no_default() -> None:
    plan = section(4)
    assert "When a key is missing (`null`), ask for it with no default" in plan
    assert "`Model: <model>` alone" in plan


def test_it_counts_the_batches_from_every_milestone() -> None:
    assert "milestones?state=all" in section(6)


def test_it_counts_the_batches_from_the_batch_issues_and_titles_the_tracking_issue() -> None:
    setup = section(6)
    assert "--state all --label batch" in setup
    assert "titled `Batch N: <goal>`" in setup


def test_the_spec_says_planning_proposes_the_cloud_and_the_model() -> None:
    planning = spec_section("3.1 Planning: owner and assistant")
    assert "go to the cloud (§12)" in planning
    assert "the model and effort, with the owner's own settings as the default" in planning


def test_the_specs_example_runs_every_independent_lane_at_once() -> None:
    example = spec_section("4.3 Batches").split("```\n", 2)[1]
    plan = parse_plan(example)
    assert plan.lanes_at_once == len(plan.lanes)
