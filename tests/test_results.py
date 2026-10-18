"""Reading what headless Claude runs return (small tests)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agent_batch.core import results

DONE: dict[str, Any] = {
    "status": "done",
    "title": "feat: x",
    "pr_body": "Body.",
    "message": "",
    "found": [{"kind": "idea", "title": "Later", "body": "Maybe."}],
}


def output(**fields: Any) -> str:
    return json.dumps({"type": "result", "is_error": False, "session_id": "s1", **fields})


def test_structured_output_with_its_numbers() -> None:
    run = results.parse_run(
        output(structured_output=DONE, total_cost_usd=0.25, permission_denials=[{}, {}])
    )
    assert run.session_id == "s1"
    assert run.data == DONE
    assert run.error is None
    assert (run.denials, run.cost_usd, run.limit_reached) == (2, 0.25, False)


def test_json_in_the_result_text_is_accepted() -> None:
    run = results.parse_run(output(result=json.dumps(DONE)))
    assert run.data == DONE


@pytest.mark.parametrize(
    ("stdout", "error"),
    [
        ("not json", "isn't JSON"),
        ("[1, 2]", "isn't an object"),
        (output(result="plain words"), "no structured output"),
        (output(is_error=True, result="Something broke."), "Something broke."),
        (output(is_error=True), "the run failed"),
    ],
)
def test_runs_that_failed(stdout: str, error: str) -> None:
    run = results.parse_run(stdout)
    assert run.data is None
    assert run.error is not None
    assert error in run.error


def test_a_usage_limit_is_recognized() -> None:
    run = results.parse_run(output(is_error=True, result="Claude usage limit reached. Resets 5pm."))
    assert run.limit_reached is True


def test_a_valid_implementation_answer() -> None:
    work = results.to_implement(DONE)
    assert work is not None
    assert work.status == "done"
    assert work.found[0].kind == "idea"


@pytest.mark.parametrize(
    "broken",
    [
        {**DONE, "status": "maybe"},
        {**DONE, "title": 3},
        {**DONE, "found": "none"},
        {**DONE, "found": [{"kind": "wish", "title": "x", "body": "y"}]},
        {**DONE, "found": [{"kind": "bug", "title": "x"}]},
        {**DONE, "found": ["text"]},
    ],
)
def test_invalid_implementation_answers(broken: dict[str, object]) -> None:
    assert results.to_implement(broken) is None


def test_a_review_with_findings() -> None:
    finding = {"severity": "high", "location": "a.py:1", "problem": "p", "suggestion": "s"}
    review = results.to_review({"verdict": "changes", "findings": [finding]})
    assert review is not None
    assert review.approved is False
    assert review.findings[0].location == "a.py:1"


@pytest.mark.parametrize(
    "broken",
    [
        {"verdict": "fine", "findings": []},
        {"verdict": "approved"},
        {"verdict": "changes", "findings": [{"severity": "high"}]},
        {"verdict": "changes", "findings": [7]},
    ],
)
def test_invalid_reviews(broken: dict[str, object]) -> None:
    assert results.to_review(broken) is None


def test_conflict_resolution_answers() -> None:
    resolved = results.to_resolve({"status": "resolved", "message": ""})
    assert resolved is not None
    assert resolved.resolved is True
    assert results.to_resolve({"status": "resolved"}) is None
    assert results.to_resolve({"status": "half", "message": ""}) is None
