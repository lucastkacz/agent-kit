"""The real `gh` lists merged PRs with their branch and the head each merged at (contract, #111).

It only reads: a branch of this repository whose PR merged, and whose head GitHub keeps.
"""

from __future__ import annotations

import pytest
from support import KIT, record

from agent_batch.shell import proc
from agent_batch.shell.github import MERGED_PR_FIELDS, GitHub

pytestmark = pytest.mark.contract

# Batch #82's lane branch for #75, squash-merged as PR #93 (the issue #111 lists its head).
BRANCH = "75-ship-keeps-the-pull-request-in-step-with"
PR, HEAD = 93, "483d5f7"
SHA_LENGTH = 40


def test_a_merged_branch_lists_its_pr_with_the_head_it_merged_at() -> None:
    args = ["gh", "pr", "list", "--head", BRANCH, "--state", "merged", "--json", MERGED_PR_FIELDS]
    record("gh-pr-list-merged", proc.must(args, KIT))

    merged = GitHub(KIT).merged_prs(BRANCH)

    assert [pr.number for pr in merged] == [PR]
    assert merged[0].branch == BRANCH
    assert merged[0].head.startswith(HEAD)


def test_the_latest_merged_prs_come_in_one_read_with_their_branch_and_head() -> None:
    args = ["gh", "pr", "list", "--state", "merged", "--limit", "200", "--json", MERGED_PR_FIELDS]
    record("gh-pr-list-recent-merged", proc.must(args, KIT))

    merged = GitHub(KIT).recent_merged_prs(200)

    assert 0 < len(merged) <= 200
    for pr in merged:
        assert pr.branch, pr
        assert len(pr.head) == SHA_LENGTH, pr
