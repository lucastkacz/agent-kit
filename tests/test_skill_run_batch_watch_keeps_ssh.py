"""run-batch's watches keep the owner's SSH, skip a second `make check`, pass lines on (#197)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_skill_run_batch_cloud_dispatch import section, skill_text
from test_skills import implement_step

OPTIONS = "-o BatchMode=yes -o ConnectTimeout=15"
SNIPPET = re.compile(r"`(ssh_command=[^`]+)`")


def owner_command(repo: Path, environment: str | None, configured: str | None) -> str:
    """The SSH command the Watch's own snippet picks, in a repository with this setup."""
    match = SNIPPET.search(section(skill_text(), "Watch"))
    assert match is not None, "the Watch gives no `ssh_command=…` to run"
    env = {"PATH": os.environ["PATH"], "HOME": str(repo), "GIT_CONFIG_NOSYSTEM": "1"}
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    if environment is not None:
        env["GIT_SSH_COMMAND"] = environment
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
    if configured is not None:
        subprocess.run(["git", "config", "core.sshCommand", configured], cwd=repo, check=True)
    script = f'{match.group(1)}\nprintf %s "$ssh_command"'
    done = subprocess.run(
        ["sh", "-c", script], cwd=repo, env=env, check=True, capture_output=True, text=True
    )
    return done.stdout


@pytest.mark.parametrize(
    ("environment", "configured", "expected"),
    [
        ("ssh -i /keys/env", "ssh -i /keys/config", "ssh -i /keys/env"),
        (None, "ssh -i /keys/config", "ssh -i /keys/config"),
        (None, None, "ssh"),
    ],
    ids=["GIT_SSH_COMMAND", "core.sshCommand", "plain ssh"],
)
def test_the_watch_adds_batch_mode_to_the_owners_own_ssh_command(
    tmp_path: Path, environment: str | None, configured: str | None, expected: str
) -> None:
    assert owner_command(tmp_path, environment, configured) == expected
    watch = section(skill_text(), "Watch")
    assert f'GIT_SSH_COMMAND="$ssh_command {OPTIONS}"' in watch, watch
    line = next(row for row in watch.splitlines() if "$ssh_command " in row)
    assert "git ls-remote origin <branch>" in line, line
    assert "instead of replacing it" in watch, watch
    assert 'GIT_SSH_COMMAND="ssh -o' not in watch, watch


def test_a_resume_runs_make_check_on_master_only_when_no_runner_is_still_running() -> None:
    resume = section(skill_text(), "Resume")
    rule = "`make check` on `master` only when no runner of the batch is still running"
    assert rule in resume, resume
    assert "`batch_finished`" in resume, resume
    assert "`agent-batch status`" in resume, resume


def test_the_rule_on_a_check_failing_outside_the_branch_is_a_case_of_failed() -> None:
    bullets = [row for row in implement_step(5).splitlines() if row.startswith("- ")]
    assert all(row.startswith("- **") for row in bullets), bullets
    failed = next(row for row in bullets if row.startswith("- **`failed`:**"))
    assert "in code your branch didn't touch" in failed, failed


def test_every_stage_of_a_watchs_pipe_passes_each_line_on_as_it_comes() -> None:
    watch = section(skill_text(), "Watch")
    assert "passes each line on as it comes" in watch, watch
    assert "`grep --line-buffered`" in watch, watch
    assert "no `cut`, `head` or `awk` without `fflush()` after it" in watch, watch
