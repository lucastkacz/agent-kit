"""The `accept-batch` skill walks the owner through a batch's acceptance (#59, SPEC §3.3)."""

from __future__ import annotations

import re

from accept_batch_skill import SKILL, section, text
from skill_files import frontmatter


def flat() -> str:
    """The skill's text in lowercase, on one line, so that a check doesn't depend on wrapping."""
    return re.sub(r"\s+", " ", text()).lower()


def test_the_accept_batch_skill_is_well_formed_and_model_invoked() -> None:
    body = text()
    fields = frontmatter(SKILL)
    assert fields["name"] == "accept-batch"
    assert "accept" in fields["description"].lower()
    assert "disable-model-invocation" not in fields
    assert "${user_config.language}" in body


def test_the_walk_follows_spec_3_3s_six_parts_in_order() -> None:
    walk = section("Walk the owner through")
    parts = [
        "### 2.1 what merged",
        "### 2.2 the high-risk prs",
        "### 2.3 the blocked questions",
        "### 2.4 the human checks",
        "### 2.5 the denials and friction",
        "### 2.6 the numbers",
    ]
    places = [walk.find(part) for part in parts]
    assert -1 not in places, dict(zip(parts, places, strict=True))
    assert places == sorted(places), dict(zip(parts, places, strict=True))


def test_it_merges_the_waiting_high_risk_prs_with_one_command() -> None:
    walk = section("Walk the owner through")
    assert "gh pr merge $pr --squash || break" in walk, walk


def test_it_reads_the_denials_from_the_events_and_the_sessions_log() -> None:
    gather = section("Gather everything")
    assert "`permission_denied`" in gather, gather
    assert ".agent-batch/batch-<n>/events.jsonl" in gather, gather
    assert ".agent-batch/denials.jsonl" in gather, gather


def test_it_compares_the_numbers_with_the_last_3_batches_and_says_when_a_bug_escaped() -> None:
    walk = section("Walk the owner through")
    assert "last 3 batches" in walk, walk
    assert "escaped" in walk, walk
    assert '"introduced by"' in walk, walk


def test_it_waits_for_the_owners_ok_before_writing_on_github_then_closes_both() -> None:
    skill = flat()
    assert "wait for the owner's ok before writing anything on github" in skill, skill
    record = section("Record the acceptance")
    assert "close the tracking issue and its milestone" in record, record


def test_an_unmerged_high_risk_pr_leaves_its_item_open_and_the_batch_unclosed() -> None:
    record = section("Record the acceptance")
    assert "high-risk pr hasn't merged" in record, record
    assert "item stays open" in record, record
    assert "asks to close the batch" in record, record


def test_it_ends_by_asking_whether_to_plan_the_next_batch_with_plan_batch() -> None:
    body = text()
    last = body[body.rindex("\n## ") :]
    assert "next batch" in last, last
    assert "`plan-batch`" in last, last
