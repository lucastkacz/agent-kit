"""A throwaway project with a git remote and fakes of `gh`, `claude` and the power tools."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from agent_batch import cli
from agent_batch.shell import system

FAKES = Path(__file__).parent / "fakes"
OWNER = "owner"
# A project's settings that enable agent-kit, as `new-project` writes them (SPEC §13).
ENABLED = '{"enabledPlugins": {"agent-kit@agent-kit": true}}\n'
# What `pmset -g batt` prints on a MacBook, by where it draws its power from.
AC_POWER = (
    "Now drawing from 'AC Power'\n"
    " -InternalBattery-0 (id=21823587)\t100%; charged; 0:00 remaining present: true\n"
)
BATTERY_POWER = (
    "Now drawing from 'Battery Power'\n"
    " -InternalBattery-0 (id=21823587)\t77%; discharging; 9:48 remaining present: true\n"
)
# Shell fakes: `caffeinate` writes down its arguments, `pmset -g batt` prints the power source.
# A test that waits on a fake executable allows at least 2 s for it to start, and checks how it
# ended, not a file it writes when it starts: macOS checks a new executable on its first run,
# which takes about 0.25 s, and over 1 s on a loaded computer (#155).
CAFFEINATE = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_CAFFEINATE_LOG"
"""
PMSET = """#!/bin/sh
[ "$*" = "-g batt" ] || exit 64
cat "$FAKE_PMSET_OUTPUT"
"""
# `systemd-inhibit` writes down its arguments, like `caffeinate`, and holds the lock at once: it
# runs its command, what follows its flags.
SYSTEMD_INHIBIT = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_SYSTEMD_INHIBIT_LOG"
while [ "${1#--}" != "$1" ]; do shift; done
exec "$@"
"""
# `tail --pid=<pid> -f /dev/null` on any computer: it lasts the pid. macOS's own `tail` has no
# `--pid`, so the command the fake `systemd-inhibit` runs would end at once with an error.
TAIL = """#!/bin/sh
pid="${1#--pid=}"
[ "$pid" != "$1" ] || exit 64
while kill -0 "$pid" 2>/dev/null; do sleep 0.1; done
"""


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
    caffeinate_log: Path
    power: Path
    systemd_inhibit_log: Path
    power_supplies: Path
    # The cores the runner is told it may use; None leaves it the computer's own count.
    cores: int | None = None

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

    def on_battery(self) -> None:
        self.power.write_text(BATTERY_POWER)

    def status_snapshots(self) -> list[dict[str, str]]:
        """The runner's status files as the fake claude's `snapshot` steps found them, in order."""
        log = self.claude_log.with_suffix(".status")
        if not log.exists():
            return []
        return [json.loads(line)["status"] for line in log.read_text().splitlines()]

    def restore_status(self, snapshot: dict[str, str]) -> None:
        """Puts the status files back as a snapshot found them, as if those runs still went on."""
        for name, text in snapshot.items():
            (self.project / ".agent-batch" / name).write_text(text)

    def caffeinate_calls(self) -> list[list[str]]:
        if not self.caffeinate_log.exists():
            return []
        return [line.split() for line in self.caffeinate_log.read_text().splitlines()]

    def systemd_inhibit_calls(self) -> list[list[str]]:
        if not self.systemd_inhibit_log.exists():
            return []
        return [line.split() for line in self.systemd_inhibit_log.read_text().splitlines()]

    def linux_power(self, *, mains_online: bool) -> None:
        """A laptop's `/sys/class/power_supply`: its mains adapter and its battery."""
        for name, kind, online in (("AC", "Mains", mains_online), ("BAT0", "Battery", True)):
            supply = self.power_supplies / name
            supply.mkdir(parents=True, exist_ok=True)
            (supply / "type").write_text(f"{kind}\n")
            (supply / "online").write_text("1\n" if online else "0\n")

    def replace_fake(self, name: str, script: str) -> None:
        """Gives this world its own `name` fake, leaving the one other worlds share alone."""
        fake = self.root / "bin" / name
        fake.unlink()
        _write_executable(fake, script)

    def run(self, *argv: str) -> int:
        cores = self.cores
        if cores is None:
            return cli.main(list(argv))
        return cli.main(list(argv), cores=lambda: cores)


def _write_executable(path: Path, script: str) -> None:
    path.write_text(script)
    path.chmod(0o755)


def _fake_scripts() -> dict[str, str]:
    fakes = {
        name: f'#!/bin/sh\nexec "{sys.executable}" "{FAKES / script}" "$@"\n'
        for name, script in (("gh", "fake_gh.py"), ("claude", "fake_claude.py"))
    }
    return fakes | {
        "caffeinate": CAFFEINATE,
        "pmset": PMSET,
        "systemd-inhibit": SYSTEMD_INHIBIT,
        "tail": TAIL,
    }


def _shared_fakes(shared: Path, fakes: dict[str, str]) -> None:
    """The fakes every world links to, written once: macOS checks a new executable on its first run.

    They are read-only, so a test that writes over one through its link fails instead of changing
    it for the tests after it; `World.replace_fake` gives a test a fake of its own.
    """
    for name, script in fakes.items():
        _write_executable(shared / name, script)
        (shared / name).chmod(0o555)
    # Each runs once now, all at a time, so that no test's timeout waits for that check. Without
    # their scenario they just fail, so what they say and how they exit don't matter.
    quiet = subprocess.DEVNULL
    runs = [
        subprocess.Popen([shared / name], env={}, stdin=quiet, stdout=quiet, stderr=quiet)
        for name in fakes
    ]
    for run in runs:
        run.wait()


@pytest.fixture(scope="session")
def shared_fakes(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The shared fakes, kept in pytest's cache by their content: later sessions find them checked.

    Each worker of a first session writes and runs its own, and the first to finish keeps them.
    """
    fakes = _fake_scripts()
    cache: pytest.Cache | None = getattr(request.config, "cache", None)
    if cache is None:
        shared = tmp_path_factory.mktemp("fakes")
        _shared_fakes(shared, fakes)
        return shared
    key = hashlib.sha256(json.dumps(fakes, sort_keys=True).encode()).hexdigest()[:16]
    kept = cache.mkdir("fakes") / key
    if not kept.is_dir():
        fresh = Path(tempfile.mkdtemp(prefix=f"{key}-", dir=kept.parent))
        _shared_fakes(fresh, fakes)
        try:
            fresh.rename(kept)
        except OSError:
            if not kept.is_dir():
                raise
            shutil.rmtree(fresh)
    return kept


@pytest.fixture(scope="session")
def git_dir() -> Path:
    """Where git keeps its commands, git itself among them, on any computer.

    macOS's /usr/bin/git looks for the developer tools' git before it runs it, on every call, which
    makes each of the suite's thousands of git calls take three times as long.
    """
    return Path(git(FAKES, "--exec-path").strip())


def _make_fakes(bin_dir: Path, shared: Path) -> None:
    bin_dir.mkdir()
    for fake in shared.iterdir():
        (bin_dir / fake.name).symlink_to(fake)


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


@pytest.fixture(scope="session")
def template_repos(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A project and its `origin`, built with git once per session for every world to copy."""
    root = tmp_path_factory.mktemp("template")
    with pytest.MonkeyPatch.context() as patch:
        for key, value in ISOLATED_GIT.items():
            patch.setenv(key, value)
        _make_repos(root)
    return root


def _copy_repos(template: Path, root: Path) -> tuple[Path, Path]:
    origin, project = root / "origin.git", root / "project"
    shutil.copytree(template / "origin.git", origin, symlinks=True)
    shutil.copytree(template / "project", project, symlinks=True)
    config = project / ".git" / "config"
    config.write_text(config.read_text().replace(str(template / "origin.git"), str(origin)))
    return origin, project


@pytest.fixture(autouse=True)
def isolated_git(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run git the same way on any computer: without its config, as a test author.

    The contract tests are the exception: they push to GitHub with the owner's own git.
    """
    if request.node.get_closest_marker("contract") is None:
        for key, value in ISOLATED_GIT.items():
            monkeypatch.setenv(key, value)


@pytest.fixture
def world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shared_fakes: Path,
    template_repos: Path,
    git_dir: Path,
) -> World:
    origin, project = _copy_repos(template_repos, tmp_path)
    _make_fakes(tmp_path / "bin", shared_fakes)
    created = World(
        root=tmp_path,
        project=project,
        origin=origin,
        gh_state=tmp_path / "gh.json",
        scenario=tmp_path / "scenario.json",
        claude_log=tmp_path / "claude.log",
        slept_file=tmp_path / "slept",
        caffeinate_log=tmp_path / "caffeinate.log",
        power=tmp_path / "pmset.txt",
        systemd_inhibit_log=tmp_path / "systemd-inhibit.log",
        power_supplies=tmp_path / "power_supply",
    )
    created.power.write_text(AC_POWER)
    created.gh_state.write_text(
        json.dumps(
            {"login": OWNER, "issues": {}, "prs": {}, "next": 100, "calls": [], "pr_views": {}}
        )
    )
    created.scenario.write_text("{}")
    monkeypatch.setenv(
        "PATH", f"{tmp_path / 'bin'}:{git_dir}:{Path(sys.executable).parent}:/usr/bin:/bin"
    )
    monkeypatch.setenv("FAKE_GH_STATE", str(created.gh_state))
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", str(created.scenario))
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(created.claude_log))
    monkeypatch.setenv("FAKE_CAFFEINATE_LOG", str(created.caffeinate_log))
    monkeypatch.setenv("FAKE_PMSET_OUTPUT", str(created.power))
    monkeypatch.setenv("FAKE_SYSTEMD_INHIBIT_LOG", str(created.systemd_inhibit_log))
    # macOS unless a test says otherwise, whatever computer runs the tests.
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(system, "POWER_SUPPLIES", created.power_supplies)
    monkeypatch.setenv("FAKE_ORIGIN", str(origin))
    monkeypatch.setenv("FAKE_SLEPT", str(created.slept_file))
    monkeypatch.setenv("FAKE_STATE_DIR", str(project / ".agent-batch"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("AGENT_BATCH_POLL_SECONDS", "0.001")
    monkeypatch.chdir(project)
    return created
