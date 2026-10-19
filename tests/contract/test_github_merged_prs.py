"""The real `gh` lists a branch's merged PRs with the head each merged at (contract test, #111).

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


def test_a_merged_branch_lists_its_pr_with_the_head_it_merged_at() -> None:
    args = ["gh", "pr", "list", "--head", BRANCH, "--state", "merged", "--json", MERGED_PR_FIELDS]
    record("gh-pr-list-merged", proc.must(args, KIT))

    merged = GitHub(KIT).merged_prs(BRANCH)

    assert [pr.number for pr in merged] == [PR]
    assert merged[0].head.startswith(HEAD)
