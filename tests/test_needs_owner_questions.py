"""A blocked question's line under "Needs the owner" stays a sentence (#54, small tests)."""

from __future__ import annotations

from agent_batch.core import report
from agent_batch.core.model import IssueReport, Outcome


def _needs(detail: str) -> str:
    text = report.render([IssueReport(13, Outcome.BLOCKED, detail)], 60)
    return text.splitlines()[-1]


def test_a_question_with_options_below_it_points_to_the_comment_in_a_sentence_of_its_own() -> None:
    detail = "Which currency should the export use?\n\nA) USD. B) ARS. I recommend A."

    assert _needs(detail) == (
        "- #13: blocked. Which currency should the export use? See #13's comment."
    )


def test_blank_lines_after_the_first_leave_nothing_to_point_to() -> None:
    assert _needs("The PR conflicts with master.\n\n  \n") == (
        "- #13: blocked. The PR conflicts with master."
    )
