"""A batch starts only on a green master, and its watch never waits on SSH (#186)."""

from __future__ import annotations

from run_batch_skill import section, skill_text
from skill_files import implement_step


def test_the_check_before_starting_runs_make_check_on_master_after_it_is_clean() -> None:
    check = section(skill_text(), "Check before starting")
    assert "`make check`" in check, check
    assert check.index("git rev-parse origin/master") < check.index("`make check`"), check
    text = skill_text()
    assert text.index("## Check before starting") < text.index("## Start"), text
    assert text.index("## Start") < text.index("## Send an issue to the cloud"), text


def test_a_failing_make_check_on_master_names_the_checks_and_stops_the_start() -> None:
    check = section(skill_text(), "Check before starting")
    assert "which checks failed" in check, check
    assert "don't start" in check, check


def test_an_implementer_answers_failed_when_a_check_fails_outside_its_branch() -> None:
    stop = implement_step(5)
    assert "didn't touch" in stop, stop
    assert "don't check master yourself" in stop, stop
    assert "answer `failed`" in stop, stop
    assert "naming the failing tests" in stop, stop
    assert "why they aren't the branch's" in stop, stop


def test_a_branch_carries_only_its_issues_work() -> None:
    text = skill_text()
    assert "only its issue's work" in text, text
    assert "its own branch" in text, text
    assert "merges first" in text, text
    assert "never commit it on another issue's branch" in text, text


def test_the_watch_runs_git_ls_remote_so_it_never_waits_for_a_prompt() -> None:
    watch = section(skill_text(), "Watch")
    command = 'GIT_SSH_COMMAND="$ssh_command -o BatchMode=yes -o ConnectTimeout=15"'
    assert command in watch, watch
    line = next(row for row in watch.splitlines() if command in row)
    assert "git ls-remote origin <branch>" in line, line
    assert "authentication" in watch, watch
    assert "fails at once" in watch, watch
