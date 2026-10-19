"""Telling GitHub's server errors from other failures, trying them again, and finding an approved
review of a head (#195, small tests)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from agent_batch.core import rounds
from agent_batch.core.model import Finding
from agent_batch.core.server_errors import is_server_error
from agent_batch.shell import retry
from agent_batch.shell.proc import CommandError


@pytest.mark.parametrize(
    "message",
    [
        "`git push --quiet` failed: remote: Internal Server Error",
        "`git push --quiet` failed: fatal: unable to access 'https://github.com/o/r.git/': "
        "The requested URL returned error: 502",
        "`gh pr create` failed: GraphQL: Something went wrong while executing your query.",
        "`gh issue edit` failed: HTTP 503: Service Unavailable (https://api.github.com/graphql)",
        "`gh issue comment` failed: HTTP 504: Gateway Timeout",
    ],
)
def test_github_s_5xx_and_graphql_failures_are_server_errors(message: str) -> None:
    assert is_server_error(message)


@pytest.mark.parametrize(
    "message",
    [
        "`git push --quiet` failed: ! [rejected] 10-x -> 10-x (fetch first)",
        "`gh pr create` failed: GraphQL: No commits between master and 10-x (createPullRequest)",
        "`gh issue edit` failed: HTTP 404: Not Found (https://api.github.com/graphql)",
        "`gh issue comment` failed: error connecting to api.github.com",
    ],
)
def test_other_failures_arent_server_errors(message: str) -> None:
    assert not is_server_error(message)


def failing(*messages: str) -> tuple[list[int], Callable[[], int]]:
    calls: list[int] = []
    left = list(messages)

    def call() -> int:
        calls.append(1)
        if left:
            raise CommandError(left.pop(0))
        return 7

    return calls, call


def test_a_call_that_passes_at_once_runs_once() -> None:
    calls, call = failing()

    assert retry.retried(call, 0) == 7
    assert len(calls) == 1


def test_a_server_error_on_the_last_try_names_the_tries_and_the_error() -> None:
    calls, call = failing(*["HTTP 500: Internal Server Error"] * retry.TRIES)

    with pytest.raises(CommandError, match=r"failed after 3 tries.*HTTP 500"):
        retry.retried(call, 0)
    assert len(calls) == retry.TRIES


def test_another_error_after_a_server_error_stops_the_tries() -> None:
    calls, call = failing("HTTP 502: Bad Gateway", "HTTP 404: Not Found")

    with pytest.raises(CommandError, match=r"^HTTP 404: Not Found$"):
        retry.retried(call, 0)
    assert len(calls) == 2


def finding(severity: str, origin: str = "new") -> Finding:
    return Finding(severity, origin, "a.py:1", "A problem.", "A fix.")


def test_an_approved_review_of_the_head_gives_the_findings_it_kept() -> None:
    kept, filed = finding("low"), finding("medium")
    earlier = (
        rounds.Round(1, "aaa", (finding("high"),)),
        rounds.Round(2, "bbb", ()),
        rounds.Round(3, "ccc", (kept, filed), approved=True),
    )

    assert rounds.approved_findings(earlier, "ccc") == (kept,)


def test_a_head_no_approved_review_read_has_no_findings_to_reuse() -> None:
    earlier = (rounds.Round(1, "aaa", (), approved=True), rounds.Round(2, "bbb", ()))

    assert rounds.approved_findings(earlier, "bbb") is None
    assert rounds.approved_findings(earlier, "ccc") is None


def test_a_reviewed_record_keeps_whether_it_approved() -> None:
    records: list[dict[str, object]] = [
        {"branch": "b", "head": "aaa", "findings": [], "approved": False},
        {"branch": "b", "head": "bbb", "findings": [], "approved": True},
        {"branch": "b", "head": "ccc", "findings": []},
    ]

    assert [r.approved for r in rounds.earlier(records, "b")] == [False, True, False]
