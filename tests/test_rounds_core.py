"""The review rounds' pure rules: what blocks, what's filed, and what the next round reads (#74)."""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import prompts, rounds
from agent_batch.core.model import Finding, ReviewResult
from agent_batch.shell.events import EventLog

BRANCH = "10-add-feature"


def finding(severity: str, origin: str, problem: str = "It breaks.") -> Finding:
    return Finding(severity, origin, "a.py:1", problem, "Fix it.")


def changes(*findings: Finding) -> ReviewResult:
    return ReviewResult(approved=False, findings=findings)


def test_an_earlier_finding_left_unanswered_still_blocks_the_third_review() -> None:
    review, filed = rounds.settle(changes(finding("medium", "earlier")), 3)

    assert not review.approved
    assert filed == ()


def test_a_filed_finding_leaves_the_nits_beside_it_to_the_approved_review() -> None:
    nit, new = finding("low", "new"), finding("medium", "new")

    review, filed = rounds.settle(changes(nit, new), 4)

    assert review == ReviewResult(approved=True, findings=(nit,))
    assert filed == (new,)


FINDINGS = st.lists(
    st.builds(
        finding,
        st.sampled_from(["high", "medium", "low"]),
        st.sampled_from(["new", "earlier", "regression"]),
    ),
    max_size=6,
).map(tuple)


@given(FINDINGS, st.integers(min_value=1, max_value=8), st.booleans())
def test_settling_files_only_new_medium_findings_from_the_third_review_and_drops_none(
    findings: tuple[Finding, ...], number: int, approved: bool
) -> None:
    review, filed = rounds.settle(ReviewResult(approved, findings), number)

    assert sorted(map(repr, review.findings + filed)) == sorted(map(repr, findings))
    assert all(f.severity == "medium" and f.origin == "new" for f in filed)
    assert number >= rounds.CONVERGES_FROM or filed == ()
    if not filed:
        assert review == ReviewResult(approved, findings)
    elif not approved:
        assert review.approved == all(f.severity == "low" for f in review.findings)


def record(branch: str, head: str, *found: Finding) -> dict[str, object]:
    fields = [f.__dict__ for f in found]
    return {"event": "reviewed", "branch": branch, "head": head, "findings": fields}


def test_the_earlier_rounds_are_the_branchs_own_reviews_in_order() -> None:
    first, second = finding("high", "new", "One."), finding("medium", "earlier", "Two.")
    records = [
        {"event": "reviewed", "issue": 10, "approved": False, "findings": 2},
        record(BRANCH, "aaa", first),
        record("11-other", "bbb", finding("low", "new")),
        record(BRANCH, "ccc", second),
    ]

    assert rounds.earlier(records, BRANCH) == (
        rounds.Round(1, "aaa", (first,)),
        rounds.Round(2, "ccc", (second,)),
    )


def test_a_first_review_asks_only_for_the_skill() -> None:
    assert prompts.review(10) == "/agent-kit:review 10"


def test_a_re_review_says_its_number_each_rounds_commit_and_which_findings_were_filed() -> None:
    kept, filed = finding("high", "new", "Kept."), finding("medium", "new", "Filed.")
    earlier = (
        rounds.Round(1, "aaa", ()),
        rounds.Round(2, "bbb", (finding("medium", "new", "Second."),)),
        rounds.Round(3, "ccc", (kept, filed)),
    )

    prompt = prompts.review(10, earlier)

    assert prompt.startswith("/agent-kit:review 10\n\n")
    assert "review 4 of this branch" in prompt
    assert "Review 1, of `aaa`: no findings." in prompt
    lines = prompt.splitlines()
    assert "Filed as an issue" not in next(line for line in lines if "Second." in line)
    assert "Filed as an issue" not in next(line for line in lines if "Kept." in line)
    assert "Filed as an issue" in next(line for line in lines if "Filed." in line)


def test_a_filed_finding_becomes_a_bug_with_its_location_and_suggestion() -> None:
    long = "The parser drops the last line of every file that has no trailing newline at its end."

    found = rounds.found_issue(Finding("medium", "new", "a.py:3", long, "Keep it."), 3)

    assert found.kind == "bug"
    assert len(found.title) <= rounds.TITLE_WIDTH
    assert found.title.endswith("…")
    for text in ("Review 3", "`a.py:3`", long, "Keep it."):
        assert text in found.body


def test_the_event_log_reads_back_its_events_of_one_kind(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    assert log.records("reviewed") == []
    log.emit("reviewed", round=1)
    log.emit("pr_opened", pr=7)
    with log.path.open("a", encoding="utf-8") as out:
        out.write(json.dumps({"event": "reviewed", "round": 2})[:-5])

    assert [r["round"] for r in log.records("reviewed")] == [1]
