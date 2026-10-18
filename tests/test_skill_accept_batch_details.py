"""The `accept-batch` skill's details beyond its acceptance tests (#59).

Where it finds the batch's PRs and denials, which earlier acceptance it counts from, who runs the
merge, where the approved issues go, and how a batch closes once its waiting PR merges. Each test
checks the few words that carry the behavior, so rewording the skill doesn't break it.
"""

from __future__ import annotations

from test_skill_accept_batch import SKILL, section
from test_skills import frontmatter


def gather() -> str:
    return section("Gather everything")


def walk() -> str:
    return section("Walk the owner through")


def has(text: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, (missing, text)


def test_it_finds_each_pr_from_its_issue_since_the_runner_sets_no_milestone_on_prs() -> None:
    assert 'search "milestone:' not in gather(), gather()
    has(gather(), "closedbypullrequestsreferences", "gh pr view", "mergedat")


def test_it_reads_the_sessions_denials_since_the_previous_acceptance() -> None:
    has(gather(), ".agent-batch/denials.jsonl", "since the previous", "whole file")


def test_it_compares_the_sessions_times_with_githubs_created_at_as_text() -> None:
    has(gather(), "`createdat`", "utc", "as text")


def test_it_counts_from_the_latest_acceptance_even_when_its_batch_is_open() -> None:
    has(gather(), "--label batch --state all", "latest", "whether or not its batch is closed")


def test_it_reads_the_cloud_runs_denials_from_their_whole_run_logs() -> None:
    has(gather(), "`cloud:`", "`list`", "`list_runs`", "`get_run_log`", "`next_cursor`")
    has(walk(), "cloud runs' logs")


def test_it_does_not_expect_an_approved_reviews_low_findings() -> None:
    has(gather(), "low findings nowhere", "in a batch", "`agent-batch ship`")


def test_the_owner_runs_the_merge_command_never_the_assistant() -> None:
    has(walk(), "for the owner to run", "you never run it")


def test_it_opens_kit_friction_in_the_kits_repository_without_naming_it() -> None:
    issues = section("Open the approved issues")
    has(issues, "project's repository", "kit's own repository", "marketplace source")
    assert "lucastkacz/agent-kit" not in issues, issues


def test_it_closes_a_batch_once_its_waiting_high_risk_pr_merged() -> None:
    has(section("Record the acceptance"), "tick that item", "without walking the batch again")
    assert "close an accepted batch" in frontmatter(SKILL)["description"]
