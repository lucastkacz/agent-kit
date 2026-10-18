"""Fixes from #59's review of `accept-batch`: where it finds PRs and denials, and who merges."""

from __future__ import annotations

from test_skill_accept_batch import SKILL, section
from test_skills import frontmatter


def test_it_finds_the_prs_from_the_milestones_issues_since_the_runner_sets_no_milestone() -> None:
    gather = section("Gather everything")
    assert 'search "milestone:' not in gather, gather
    assert "closedbypullrequestsreferences" in gather, gather
    assert "gh pr view <pr> --json labels,state,mergedat,body" in gather, gather


def test_it_reads_the_sessions_denials_since_the_previous_acceptance() -> None:
    gather = section("Gather everything")
    assert "since the previous batch's acceptance comment" in gather, gather
    assert "the whole file when no batch has been accepted yet" in gather, gather


def test_it_reads_the_cloud_runs_denials_from_their_run_logs() -> None:
    gather = section("Gather everything")
    assert "`cloud:` line" in gather, gather
    assert "`get_run_log`" in gather, gather
    assert "cloud runs' logs" in section("Walk the owner through")


def test_it_does_not_expect_an_approved_reviews_low_findings() -> None:
    gather = section("Gather everything")
    assert "keeps its low findings nowhere" in gather, gather
    assert "in a batch or in `agent-batch ship`" in gather, gather


def test_it_reads_the_acceptance_comments_of_open_batches_too() -> None:
    gather = section("Gather everything")
    assert "gh issue list --label batch --state all" in gather, gather
    assert "the latest such comment's `createdat`, whether or not its batch is closed" in gather


def test_it_compares_the_sessions_times_with_githubs_created_at() -> None:
    gather = section("Gather everything")
    assert "`createdat` are both utc iso times of the same width up to the seconds" in gather


def test_it_names_the_path_to_a_cloud_runs_whole_log() -> None:
    gather = section("Gather everything")
    for step in ("`list`", "`list_runs`", "`get_run_log`", "`next_cursor`"):
        assert step in gather, (step, gather)


def test_the_owner_runs_the_merge_command_never_the_assistant() -> None:
    walk = section("Walk the owner through")
    assert "for the owner to run; you never run it" in walk, walk


def test_it_opens_kit_friction_in_the_kits_repository_without_naming_it() -> None:
    issues = section("Open the approved issues")
    assert "the project's repository" in issues, issues
    assert "the kit's own repository, the plugin's marketplace source" in issues, issues
    assert "lucastkacz/agent-kit" not in issues, issues


def test_it_closes_a_batch_once_its_waiting_high_risk_pr_merged() -> None:
    record = section("Record the acceptance")
    assert "tick that item, and close the tracking issue and the milestone" in record, record
    assert "close an accepted batch" in frontmatter(SKILL)["description"]
