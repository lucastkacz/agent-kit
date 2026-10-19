"""protect-master lets a pull on `master` through only when it may only fast-forward (#86)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_hooks import protect_master
from agent_hooks.commands import git_calls

HERE = Path("/repo")


def refusal(command: str, branch: str) -> str | None:
    found = git_calls(command, HERE)
    reasons = [protect_master.refusal(call, lambda _: branch) for call in found]
    return next((reason for reason in reasons if reason), None)


@pytest.mark.parametrize(
    "command",
    [
        "git pull",
        "git pull origin master",
        "git pull --no-ff",
        "git pull --ff",
        "git pull --rebase",
    ],
)
@pytest.mark.parametrize("branch", ["master", "main"])
def test_a_pull_without_ff_only_on_a_protected_branch_is_blocked(command: str, branch: str) -> None:
    assert refusal(command, branch)


@pytest.mark.parametrize(
    "command",
    ["git pull --ff-only", "git pull --ff-only origin master", "git pull --rebase --ff-only"],
)
def test_a_fast_forward_only_pull_on_master_runs(command: str) -> None:
    assert refusal(command, "master") is None


def test_a_later_no_ff_undoes_ff_only_on_a_pull() -> None:
    assert refusal("git pull --ff-only --no-ff", "master")


def test_the_refusal_of_a_pull_on_master_names_git_pull_ff_only() -> None:
    reason = refusal("git pull", "master")
    assert reason is not None
    assert "`git pull --ff-only`" in reason


@pytest.mark.parametrize("command", ["git pull", "git pull --no-ff"])
def test_a_pull_on_a_working_branch_runs(command: str) -> None:
    assert refusal(command, "12-export") is None
