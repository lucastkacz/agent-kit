"""The interview skill settles each issue's design decisions with the owner (#253)."""

from __future__ import annotations

from interview_skill import SKILL, section, text
from skill_files import check_well_formed, frontmatter


def test_the_skill_exists_and_triggers_on_an_interview_of_an_issue() -> None:
    assert (SKILL / "SKILL.md").is_file(), f"{SKILL} has no SKILL.md"
    check_well_formed(SKILL)
    fields = frontmatter(SKILL)
    assert "disable-model-invocation" not in fields
    description = fields["description"].lower()
    for trigger in ("interview", "issue", "plan-batch"):
        assert trigger in description, f"the description doesn't trigger on {trigger!r}"
    assert "${user_config.language}" in text()


def test_it_credits_mattpocock_skills_grilling_under_its_license() -> None:
    skill = text()
    assert "`grilling`" in skill
    assert "mattpocock/skills (MIT)" in skill


def test_the_decisions_form_a_design_tree_worked_in_rounds_of_the_frontier() -> None:
    assert "The decisions form a design tree" in section(2)
    rounds = section(3)
    assert "Work the tree in rounds" in rounds
    assert "Each round asks the whole frontier" in rounds
    assert "every open decision whose prerequisites are settled" in rounds


def test_each_question_is_numbered_with_a_recommendation_that_yes_accepts() -> None:
    rounds = section(3)
    assert "Number each question and give your recommended answer" in rounds
    assert 'worded so that "yes" accepts it' in rounds
    assert "`1. " in rounds, "the rounds show no numbered example"


def test_a_question_waits_while_one_it_depends_on_is_open() -> None:
    assert "A question that depends on another one still open waits for a later round" in section(3)


def test_facts_are_looked_up_by_subagents_and_decisions_left_to_the_owner() -> None:
    tree = section(2)
    assert "Facts are yours to find, never the owner's" in tree
    assert "read-only `Explore` subagents" in tree
    assert "Decisions are the owner's" in tree


def test_it_ends_only_when_the_frontier_is_empty_and_the_owner_confirms() -> None:
    rounds = section(3)
    assert "done only when the frontier is empty and the owner confirms" in rounds


def test_it_writes_each_answer_into_the_issues_fields() -> None:
    answers = section(4)
    assert "Write each answer into the issue's fields" in answers
    for field in ("Briefing", "Acceptance criteria", "Out of scope", "Stop and ask if"):
        assert field in answers, field
    assert "for a bug, its own fields plus its criteria" in answers
    assert "gh issue edit <n> --body-file <file>" in answers


def test_a_decision_that_binds_more_than_the_issue_goes_into_an_adr() -> None:
    answers = section(4)
    assert "A decision that binds more than the issue" in answers
    assert "goes into an ADR in `docs/adr/`" in answers
    assert "`docs/adr/0001-a-plugin-agent-for-the-cloud-routines.md`" in answers


def test_the_ready_check_runs_one_read_only_subagent_per_issue_in_parallel() -> None:
    check = section(5)
    assert "one read-only `Explore` subagent per issue" in check
    assert "in the same message so that they run in parallel" in check
    assert "and to change nothing" in check


def test_the_ready_check_runs_at_the_implementers_model() -> None:
    check = section(5)
    assert "at the implementer's model" in check
    assert "the batch's `Model:` line's model" in check
    assert "the owner's own `model` setting when there's none" in check
    assert "the Agent tool's `model`" in check


def test_the_ready_check_lists_the_decisions_it_would_have_to_guess() -> None:
    check = section(5)
    assert "lists the decisions it would have to guess, not the facts it can look up" in check


def test_the_checks_questions_go_back_to_the_interview_never_as_blocked() -> None:
    check = section(5)
    assert "Its questions go back to the interview" in check
    assert "before the owner approves the batch: never as `blocked`" in check


def test_after_two_checks_that_still_find_some_the_owner_decides() -> None:
    check = section(5)
    assert "After two checks that still find some, the owner decides" in check
    assert "goes in as it is or stays out of the batch" in check


def test_the_skill_never_labels_an_issue_ready() -> None:
    assert "Never label an issue `ready`" in text()
    assert "--add-label" not in text()
