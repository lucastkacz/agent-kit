"""The battery check's edge cases, and a batch refused on battery (#29)."""

from __future__ import annotations

import io
import json

import pytest

from agent_batch.shell import system
from agent_hooks import session_start
from conftest import World

BATCH = 1


def test_a_refused_batch_on_battery_leaves_no_batch_running_for_the_next_session(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.on_battery()
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n", author="someone-else")

    assert world.run("run", str(BATCH)) == 1

    payload = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(world.project)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert session_start.main() == 0
    assert "is running, or stopped halfway" not in out.getvalue()


def test_a_pmset_that_cant_run_counts_as_not_on_battery(world: World) -> None:
    (world.root / "bin" / "pmset").write_text("#!/nonexistent/sh\n")

    assert not system.on_battery()


def test_a_pmset_that_hangs_counts_as_not_on_battery(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    (world.root / "bin" / "pmset").write_text("#!/bin/sh\nexec sleep 5\n")
    monkeypatch.setattr(system, "PMSET_TIMEOUT", 0.1)

    assert not system.on_battery()


def test_a_pmset_output_that_isnt_text_counts_as_not_on_battery(world: World) -> None:
    (world.root / "bin" / "pmset").write_text("#!/bin/sh\nprintf '\\377\\376 not text'\n")

    assert not system.on_battery()
