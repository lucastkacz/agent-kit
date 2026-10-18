"""The hook that keeps commits and pushes off `master` (#11)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from agent_hooks import protect_master
from agent_hooks.commands import git_calls
from conftest import ENABLED, git

HERE = Path("/repo")


def calls(command: str) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(str(c.directory), c.subcommand, c.args) for c in git_calls(command, HERE)]


def test_quotes_and_heredocs_are_text_not_commands() -> None:
    assert calls("echo 'git commit -m x' && printf \"git push origin master\"") == []
    heredoc = "cat > notes.md <<'EOF'\ngit commit -m x\ngh pr merge 3\nEOF\ngit status"
    assert calls(heredoc) == [("/repo", "status", ())]
    assert calls('git commit -m "never git push origin master"') == [
        ("/repo", "commit", ("-m", "never git push origin master"))
    ]


def test_chains_options_folders_and_cd_are_followed() -> None:
    command = "cd sub && FOO=1 git -c a.b=c -C ../wt commit -m x; git -C /abs push origin HEAD"
    assert calls(command) == [
        ("/repo/wt", "commit", ("-m", "x")),
        ("/abs", "push", ("origin", "HEAD")),
    ]
    assert calls("git status | head\ngit log") == [("/repo", "status", ()), ("/repo", "log", ())]


def test_a_command_that_doesnt_parse_runs_nothing_so_it_passes() -> None:
    assert calls("git commit -m 'unbalanced") == []


def refusal(command: str, branch: str) -> str | None:
    found = git_calls(command, HERE)
    reasons = [protect_master.refusal(call, lambda _: branch) for call in found]
    return next((reason for reason in reasons if reason), None)


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git add -A && git commit -m x",
        "git merge 12-export",
        "git rebase 12-export",
        "git reset --soft HEAD~1",
        "git cherry-pick abc123",
        "git push",
        "git push origin",
        "git push -u origin HEAD",
    ],
)
def test_writing_to_master_from_master_is_denied(command: str) -> None:
    assert refusal(command, "master")
    assert refusal(command, "main")


@pytest.mark.parametrize(
    "command",
    [
        "git push origin HEAD:master",
        "git push origin 12-export:refs/heads/master",
        "git push origin +master",
        "git push origin :main",
        "git push --all origin",
    ],
)
def test_pushing_to_master_from_a_branch_is_denied(command: str) -> None:
    assert refusal(command, "12-export")


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git merge origin/master",
        "git push origin 12-export",
        "git push -u origin HEAD",
        "git status && git log --oneline -3",
    ],
)
def test_the_same_commands_on_a_branch_pass(command: str) -> None:
    assert refusal(command, "12-export") is None


def test_pulling_on_master_passes() -> None:
    assert refusal("git pull --ff-only", "master") is None


def run_hook(command: str, cwd: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert protect_master.main() == 0
    return out.getvalue()


def test_the_hook_reads_the_real_branch_of_each_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    git(tmp_path, "init", "--quiet", "-b", "master", str(repo))
    git(repo, "commit", "--quiet", "--allow-empty", "-m", "chore: start")
    git(repo, "worktree", "add", "--quiet", "-b", "12-export", str(tmp_path / "lane"))
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text(ENABLED)

    denied = json.loads(run_hook("git commit -m x", repo, monkeypatch))
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "master" in denied["hookSpecificOutput"]["permissionDecisionReason"]
    assert run_hook(f"git -C {tmp_path / 'lane'} commit -m x", repo, monkeypatch) == ""
    assert run_hook("echo 'git commit' > notes.txt", repo, monkeypatch) == ""
