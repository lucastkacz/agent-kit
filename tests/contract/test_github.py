"""The real `gh` answers the way the runner reads it, on this repository (contract tests).

Run them with `make contract`. They open an issue and a PR here and close them. The PR's checks
fail on purpose, so its armed auto-merge never merges anything.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from support import KIT, record, unique

from agent_batch.core import merge
from agent_batch.core.config import HIGH_RISK, Config
from agent_batch.core.merge import MergeStatus
from agent_batch.core.model import Closure
from agent_batch.shell import proc
from agent_batch.shell.git import Git
from agent_batch.shell.github import CLOSURE_FIELDS, ISSUE_FIELDS, PR_FIELDS, GitHub

pytestmark = pytest.mark.contract

CHECKS_TIMEOUT = 300
POLL_SECONDS = 10
LABEL_TIMEOUT = 60
LABEL_POLL_SECONDS = 5


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    url = proc.must(["git", "remote", "get-url", "origin"], KIT).strip()
    proc.must(["git", "clone", "--quiet", "--depth", "1", url, str(tmp_path / "kit")], tmp_path)
    return tmp_path / "kit"


def test_issues_are_created_read_labeled_and_commented(clone: Path) -> None:
    gh = GitHub(clone)
    title = unique("contract-issue")
    number = gh.create_issue(title, "Opened by a contract test.\n\n### Risk\n\nLow\n", "task")
    try:
        raw = proc.must(["gh", "issue", "view", str(number), "--json", ISSUE_FIELDS], clone)
        record("gh-issue-view", raw)
        issue = gh.issue(number)
        assert (issue.number, issue.title, issue.state) == (number, title, "OPEN")
        assert issue.author == gh.login()
        assert issue.labels == {"task"}

        gh.add_label(number, "blocked")
        gh.comment(number, "A contract test's comment.")
        assert "blocked" in gh.issue(number).labels
    finally:
        proc.must(["gh", "issue", "close", str(number), "--reason", "not planned"], clone)
    raw = proc.must(["gh", "issue", "view", str(number), "--json", CLOSURE_FIELDS], clone)
    record("gh-issue-closure", raw)
    assert gh.closure(number) == Closure(reason="NOT_PLANNED", prs=())


def test_a_pr_with_failing_checks_keeps_its_auto_merge_armed_and_never_merges(clone: Path) -> None:
    gh, git = GitHub(clone), Git(Config())
    branch = unique("contract-pr")
    _commit_breaking_change(clone, branch)
    git.push(clone, branch)
    number = None
    try:
        title = "test: a contract PR that must not merge"
        number = gh.create_pr(branch, "master", title, "Its checks fail on purpose.")
        assert gh.find_pr(branch) == number
        _edit_and_check(gh, clone, number)
        sha = git.head(clone)
        gh.arm_merge(number, sha)
        # `find_pr(branch, label)` finds the PR only once it has the label (#120).
        assert gh.find_pr(branch, HIGH_RISK) is None
        gh.pr_add_label(number, HIGH_RISK)
        assert _wait_for_a_labeled_pr(gh, branch) == number
        gh.pr_comment(number, "A contract test's comment.")

        assert _wait_for_a_decision(gh, number) is MergeStatus.CHECKS_FAILED
        record(
            "gh-pr-view", proc.must(["gh", "pr", "view", str(number), "--json", PR_FIELDS], clone)
        )
        assert gh.pr_state(number).head_sha == sha
    finally:
        if number is not None:
            proc.run(["gh", "pr", "close", str(number), "--delete-branch"], clone)
        else:
            proc.run(["git", "push", "--quiet", "origin", "--delete", branch], clone)


def _edit_and_check(gh: GitHub, clone: Path, number: int) -> None:
    title, body = "test: a contract PR, edited", "Its checks still fail on purpose."
    gh.edit_pr(number, title, body)
    raw = proc.must(["gh", "pr", "view", str(number), "--json", "title,body"], clone)
    edited = json.loads(raw)
    assert (edited["title"], edited["body"].strip()) == (title, body)


def _commit_breaking_change(clone: Path, branch: str) -> None:
    proc.must(["git", "switch", "--quiet", "--create", branch], clone)
    # A syntax error that `make check` rejects, so the PR's required check fails.
    (clone / "tools" / f"{branch.replace('-', '_')}.py").write_text("broken = (\n")
    proc.must(["git", "add", "-A"], clone)
    proc.must(["git", "commit", "--quiet", "-m", "test: a contract PR that must not merge"], clone)


def _wait_for_a_labeled_pr(gh: GitHub, branch: str) -> int | None:
    """GitHub may take a few seconds to list a PR by a label it was just given."""
    deadline = time.monotonic() + LABEL_TIMEOUT
    while (found := gh.find_pr(branch, HIGH_RISK)) is None and time.monotonic() < deadline:
        time.sleep(LABEL_POLL_SECONDS)
    return found


def _wait_for_a_decision(gh: GitHub, number: int) -> MergeStatus:
    deadline = time.monotonic() + CHECKS_TIMEOUT
    while time.monotonic() < deadline:
        status = merge.decide(gh.pr_state(number))
        if status is not MergeStatus.WAIT:
            return status
        time.sleep(POLL_SECONDS)
    return MergeStatus.TIMED_OUT
