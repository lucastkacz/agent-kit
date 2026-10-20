"""A batch of many lanes loads the computer less (#198).

The lanes' worktrees go where macOS's Spotlight doesn't index them, and many lanes at once share
the computer's cores among their tests. `agent-batch run` runs with real git and fake `gh` and
`claude` (medium tests); the Makefile's tests ask `make` what it would run.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import World

BATCH = 1
KIT = Path(__file__).parent.parent
TODAY = 4


def _run_lanes(world: World, lanes: int, *flags: str) -> int:
    """A batch of `lanes` lanes, one issue each, of which only one starts."""
    plan = ""
    for lane in range(1, lanes + 1):
        world.add_issue(10 + lane)
        plan += f"Lane {lane}: #{10 + lane}\n"
    world.add_batch(BATCH, f"{plan}Lanes: {lanes}\n")
    return world.run("run", "--max-issues", "1", *flags, str(BATCH))


def _lane_folders(world: World) -> set[str]:
    project = world.project.resolve()
    return {
        Path(call["cwd"]).resolve().relative_to(project).parent.as_posix()
        for call in world.claude_calls()
    }


def _workers(world: World) -> set[str | None]:
    calls = world.claude_calls()
    assert calls, "no claude run started"
    return {call["pytest_workers"] for call in calls}


@pytest.fixture
def cores(world: World, monkeypatch: pytest.MonkeyPatch) -> int:
    """A computer of 10 cores, as the owner's, where the tests don't choose their own workers."""
    world.cores = 10
    monkeypatch.delenv("PYTEST_WORKERS", raising=False)
    return 10


def test_on_macos_the_lanes_worktrees_are_in_a_folder_spotlight_skips(world: World) -> None:
    assert _run_lanes(world, 1) == 0

    [folder] = _lane_folders(world)
    assert folder.startswith(".agent-batch/"), folder
    assert folder.endswith(".noindex"), f"Spotlight indexes {folder}"


def test_on_linux_the_lanes_worktrees_stay_where_they_were(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    world.linux_power(mains_online=True)

    assert _run_lanes(world, 1) == 0

    assert _lane_folders(world) == {".agent-batch/worktrees"}


@pytest.mark.parametrize("lanes", [4, 6])
def test_more_than_three_lanes_at_once_share_the_cores_among_their_test_workers(
    world: World, cores: int, lanes: int
) -> None:
    assert _run_lanes(world, lanes) == 0

    [workers] = _workers(world)
    assert workers is not None, "the lanes' tests run as many workers as ever"
    assert 1 <= int(workers) < TODAY
    assert int(workers) * lanes <= cores, f"{lanes} lanes run {workers} workers each"


@pytest.mark.usefixtures("cores")
def test_more_lanes_than_run_at_once_count_only_those_that_run(world: World) -> None:
    assert _run_lanes(world, 6, "--lanes", "3") == 0

    assert _workers(world) == {None}


@pytest.mark.usefixtures("cores")
@pytest.mark.parametrize("lanes", [1, 3])
def test_three_lanes_or_fewer_run_pytest_as_today(world: World, lanes: int) -> None:
    assert _run_lanes(world, lanes) == 0

    assert _workers(world) == {None}


def _dry_run(target: str, env: dict[str, str]) -> list[str]:
    done = subprocess.run(
        ["make", "-n", "-f", str(KIT / "Makefile"), target],
        cwd=KIT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in done.stdout.splitlines() if "pytest" in line]


# What a `make` that runs these tests hands the one they start, which would change its answer.
MAKE_OWN = frozenset({"PYTEST_WORKERS", "MAKEFLAGS", "MFLAGS", "MAKELEVEL"})


@pytest.mark.parametrize("target", ["test", "check"])
def test_the_makefile_runs_the_workers_a_batch_hands_it(target: str) -> None:
    env = {key: value for key, value in os.environ.items() if key not in MAKE_OWN}

    today = _dry_run(target, env)
    lowered = _dry_run(target, {**env, "PYTEST_WORKERS": "2"})

    assert today, f"make {target} runs no pytest"
    assert all(f"-n {TODAY}" in line for line in today), today
    assert all("-n 2" in line for line in lowered), lowered
