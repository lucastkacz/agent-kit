"""A throwaway project with a git remote, a fake `gh` and a fake `claude` on the PATH."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from agent_batch import cli

FAKES = Path(__file__).parent / "fakes"
OWNER = "owner"
# A project's settings that enable agent-kit, as `new-project` writes them (SPEC §13).
ENABLED = '{"enabledPlugins": {"agent-kit@agent-kit": true}}\n'


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout


@dataclass
class World:
    root: Path
    project: Path
    origin: Path
    gh_state: Path
    scenario: Path
    claude_log: Path
    slept_file: Path

    def gh(self) -> dict[str, Any]:
        state: dict[str, Any] = json.loads(self.gh_state.read_text())
        return state

    def _save_gh(self, state: dict[str, Any]) -> None:
        self.gh_state.write_text(json.dumps(state))

    def add_issue(
        self,
        number: int,
        *,
        risk: str = "Low",
        labels: tuple[str, ...] = ("task", "ready"),
        author: str = OWNER,
    ) -> None:
        body = (
            "### Goal\n\nSomething useful.\n\n### Acceptance criteria\n\n"
            "- [ ] It works. Verify: unit\n- [ ] It feels right. Verify: human(taste)\n\n"
            f"### Risk\n\n{risk}\n"
        )
        self._put_issue(number, f"Issue {number}", body, labels, author)

    def add_batch(self, number: int, body: str, *, author: str = OWNER) -> None:
        self._put_issue(number, "Batch", body, ("batch",), author)

    def _put_issue(
        self, number: int, title: str, body: str, labels: tuple[str, ...], author: str
    ) -> None:
        state = self.gh()
        state["issues"][str(number)] = {
            "number": number,
            "title": title,
            "body": body,
            "author": author,
            "labels": list(labels),
            "state": "OPEN",
            "comments": [],
        }
        self._save_gh(state)

    def script(self, kind: str, number: int, *steps: dict[str, Any]) -> None:
        scenario = json.loads(self.scenario.read_text())
        scenario.setdefault(kind, {})[str(number)] = list(steps)
        self.scenario.write_text(json.dumps(scenario))

    def pr_views(self, branch: str, *views: dict[str, Any]) -> None:
        state = self.gh()
        state["pr_views"][branch] = list(views)
        self._save_gh(state)

    def claude_calls(self) -> list[dict[str, Any]]:
        if not self.claude_log.exists():
            return []
        return [json.loads(line) for line in self.claude_log.read_text().splitlines()]

    def slept(self) -> float:
        """The seconds the fake claude's `slept` steps said the computer slept."""
        return float(self.slept_file.read_text()) if self.slept_file.exists() else 0.0

    def run(self, *argv: str) -> int:
        return cli.main(list(argv))


def _make_fakes(bin_dir: Path) -> None:
    bin_dir.mkdir()
    for name, script in (("gh", "fake_gh.py"), ("claude", "fake_claude.py")):
        wrapper = bin_dir / name
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKES / script}" "$@"\n')
        wrapper.chmod(0o755)


def _make_repos(root: Path) -> tuple[Path, Path]:
    origin, seed, project = root / "origin.git", root / "seed", root / "project"
    git(root, "init", "--quiet", "--bare", "-b", "master", str(origin))
    git(root, "clone", "--quiet", str(origin), str(seed))
    (seed / ".gitignore").write_text(".agent-batch/\n")
    (seed / "README.md").write_text("A project.\n")
    (seed / ".claude").mkdir()
    (seed / ".claude" / "settings.json").write_text(ENABLED)
    git(seed, "add", "-A")
    git(seed, "commit", "--quiet", "-m", "chore: start")
    git(seed, "push", "--quiet", "origin", "HEAD:master")
    git(root, "clone", "--quiet", str(origin), str(project))
    return origin, project


ISOLATED_GIT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Tester",
    "GIT_AUTHOR_EMAIL": "tester@example.com",
    "GIT_COMMITTER_NAME": "Tester",
    "GIT_COMMITTER_EMAIL": "tester@example.com",
}


@pytest.fixture(autouse=True)
def isolated_git(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run git the same way on any computer: without its config, as a test author.

    The contract tests are the exception: they push to GitHub with the owner's own git.
    """
    if request.node.get_closest_marker("contract") is None:
        for key, value in ISOLATED_GIT.items():
            monkeypatch.setenv(key, value)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    origin, project = _make_repos(tmp_path)
    _make_fakes(tmp_path / "bin")
    created = World(
        root=tmp_path,
        project=project,
        origin=origin,
        gh_state=tmp_path / "gh.json",
        scenario=tmp_path / "scenario.json",
        claude_log=tmp_path / "claude.log",
        slept_file=tmp_path / "slept",
    )
    created.gh_state.write_text(
        json.dumps(
            {"login": OWNER, "issues": {}, "prs": {}, "next": 100, "calls": [], "pr_views": {}}
        )
    )
    created.scenario.write_text("{}")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:{Path(sys.executable).parent}:/usr/bin:/bin")
    monkeypatch.setenv("FAKE_GH_STATE", str(created.gh_state))
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", str(created.scenario))
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(created.claude_log))
    monkeypatch.setenv("FAKE_ORIGIN", str(origin))
    monkeypatch.setenv("FAKE_SLEPT", str(created.slept_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("AGENT_BATCH_POLL_SECONDS", "0")
    monkeypatch.chdir(project)
    return created
