"""The follow-up issue's pure rules: its text, which issue a PR has, and its label (#136)."""

from __future__ import annotations

from agent_batch.core import followup
from agent_batch.core.model import FoundIssue

BRANCH = "10-add-feature"
DATES = FoundIssue("idea", "Dates drift", "Seen in the importer.\n")
CACHE = FoundIssue("bug", "Cache breaks", "It keeps stale files.")


def test_one_item_keeps_its_own_title_kind_and_body() -> None:
    found = followup.issue([DATES], 10)

    body = "Seen in the importer.\n\nFound while working on #10."
    assert found == FoundIssue("idea", "Dates drift", body)


def test_several_items_go_under_one_title_each_in_its_own_section() -> None:
    found = followup.issue([DATES, CACHE], 10)

    assert (found.kind, found.title) == ("bug", "Follow-ups of #10")
    assert "## Idea: Dates drift\n\nSeen in the importer.\n\n## Bug: Cache breaks" in found.body
    assert found.body.endswith("\n\nFound while working on #10.")


def test_the_prs_follow_up_is_the_last_one_its_branch_filed() -> None:
    records = [
        {"event": "issue_found", "issue": 10, "found": 20},  # before #136: no branch
        {"event": "issue_found", "issue": 10, "branch": BRANCH, "found": 21},
        {"event": "issue_found", "issue": 11, "branch": "11-other", "found": 22},
        {"event": "issue_found", "issue": 10, "branch": BRANCH, "found": 23},
    ]

    assert followup.existing(records, BRANCH) == 23
    assert followup.existing(records, "12-none") is None


def test_a_more_severe_item_swaps_the_follow_ups_kind_label() -> None:
    assert followup.relabel(["idea", "batch-6"], [CACHE]) == ("bug", frozenset({"idea"}))


def test_a_less_severe_item_leaves_the_follow_ups_label_alone() -> None:
    assert followup.relabel(["bug"], [DATES]) is None
