"""SPEC §3.1 describes the interview and the ready check (#253)."""

from __future__ import annotations

from spec_text import flat_spec_section

PLANNING = "3.1 Planning: owner and assistant"


def test_planning_interviews_the_owner_in_rounds() -> None:
    planning = flat_spec_section(PLANNING)
    assert "interviews the owner with the `interview` skill" in planning
    assert "each round asks every decision whose prerequisites are settled" in planning
    assert 'a recommended answer that "yes" accepts' in planning
    assert "looks up the facts itself" in planning


def test_the_answers_go_into_the_issues_and_wider_decisions_into_an_adr() -> None:
    planning = flat_spec_section(PLANNING)
    assert "the answers go into the issue's fields" in planning
    assert "binds more than the issue goes into an adr" in planning


def test_a_ready_check_reads_each_issue_as_its_implementer_would() -> None:
    planning = flat_spec_section(PLANNING)
    assert "a ready check reads each issue as its implementer would" in planning
    assert "one read-only subagent per issue, in parallel, at the implementer's model" in planning
    assert "the decisions it would have to guess" in planning


def test_the_checks_questions_go_back_to_the_interview() -> None:
    planning = flat_spec_section(PLANNING)
    assert "its questions go back to the interview, never to `blocked`" in planning
    assert "after two checks that still find some, the owner decides" in planning
