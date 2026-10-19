"""A line under "Needs the owner" in the batch summary reads as a sentence (#54, small tests)."""

from __future__ import annotations

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from agent_batch.core import report
from agent_batch.core.model import IssueReport, Outcome

HEADING = "### Needs the owner\n\n"
REVIEW_DETAIL = (
    "The review still asks for changes after 2 rounds:\n\n"
    "- **high** `core/report.py:89`: the line drops the findings."
)
# Plain text rarely ends a line in a colon; these characters make it likely.
DETAILS = st.text(alphabet=": .?\na\r") | st.text()


def _line(outcome: Outcome, detail: str) -> str:
    """The one line the summary writes under its heading for issue #29 (PR #31)."""
    text = report.render([IssueReport(29, outcome, detail, pr=31)], 60)
    return text.split(HEADING, 1)[1].removesuffix("\n")


def _today(outcome: Outcome, detail: str) -> str:
    """The line as the summary wrote it before #54, with no period after a `?` or `!` (#127)."""
    target = "#31" if outcome is Outcome.WAITING_OWNER else "#29"
    first = detail.splitlines()[0] if detail else ""
    line = f"- {target}: {outcome.value}. {first}".rstrip(". ")
    return line if line.endswith(("?", "!")) else line + "."


@pytest.mark.parametrize("outcome", [Outcome.BLOCKED, Outcome.FAILED])
def test_a_multi_line_detail_keeps_its_first_line_without_the_colon_and_points_to_the_comment(
    outcome: Outcome,
) -> None:
    assert _line(outcome, REVIEW_DETAIL) == (
        f"- #29: {outcome.value}. The review still asks for changes after 2 rounds; "
        "see #29's comment."
    )


ONE_LINE_DETAILS = [
    (Outcome.BLOCKED, "The PR conflicts with master.", "blocked. The PR conflicts with master."),
    (Outcome.FAILED, "the run failed: timeout\n", "failed. the run failed: timeout."),
    (Outcome.WAITING_OWNER, "it's high risk", "waiting for the owner. it's high risk."),
    (Outcome.BLOCKED, "", "blocked."),
]


@pytest.mark.parametrize(("outcome", "detail", "said"), ONE_LINE_DETAILS)
def test_a_one_line_detail_reads_as_it_does_today(outcome: Outcome, detail: str, said: str) -> None:
    target = "#31" if outcome is Outcome.WAITING_OWNER else "#29"
    assert _line(outcome, detail) == f"- {target}: {said}"


@given(st.sampled_from(report.NEEDS_OWNER), DETAILS)
def test_any_one_line_detail_reads_as_it_does_today(outcome: Outcome, detail: str) -> None:
    assume(len(detail.splitlines()) <= 1)
    assume(not _today(outcome, detail).endswith(":."))

    assert _line(outcome, detail) == _today(outcome, detail)


@pytest.mark.parametrize("detail", [REVIEW_DETAIL, "The review still asks for changes:", "Why: :."])
def test_no_line_under_needs_the_owner_ends_in_a_colon_and_a_period(detail: str) -> None:
    assert not _line(Outcome.BLOCKED, detail).endswith(":.")


@given(st.sampled_from(report.NEEDS_OWNER), DETAILS)
def test_no_detail_makes_its_line_end_in_a_colon_and_a_period(
    outcome: Outcome, detail: str
) -> None:
    assert not _line(outcome, detail).endswith(":.")
