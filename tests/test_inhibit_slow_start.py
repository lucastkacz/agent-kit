"""A `systemd-inhibit` that fails or holds counts as such however slowly it starts (#185)."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

import test_inhibit_failure_and_unreadable_supply as failure
from agent_batch.shell import system
from conftest import World

# Slower than the old 0.5 s window, as a loaded computer or macOS's first-run check can be.
SLOW_FAILING_INHIBIT = """#!/bin/sh
sleep 1
echo "Failed to inhibit: Access denied" >&2
exit 1
"""
# `systemd-inhibit` runs its command, what follows its flags, once it holds the lock.
SLOW_HOLDING_INHIBIT = """#!/bin/sh
sleep 1
while [ "${1#--}" != "$1" ]; do shift; done
exec "$@"
"""


def _tail(started: Path) -> str:
    """`tail --pid=<pid> -f /dev/null` on any computer: it says it started, and lasts the pid."""
    return f"""#!/bin/sh
touch "{started}"
pid="${{1#--pid=}}"
while kill -0 "$pid" 2>/dev/null; do sleep 0.1; done
"""


def _stuck_inhibit(pid_file: Path) -> str:
    """One that neither takes its lock nor exits, as when the system bus never answers."""
    return f"""#!/bin/sh
echo $$ > "{pid_file}"
exec sleep 30
"""


def _end(hold: subprocess.Popen[bytes] | None) -> None:
    if hold is not None:
        hold.terminate()
        hold.wait()


def test_a_systemd_inhibit_that_fails_after_a_slow_start_holds_nothing(world: World) -> None:
    world.replace_fake("systemd-inhibit", SLOW_FAILING_INHIBIT)

    hold = system.keep_awake("linux")
    _end(hold)

    assert hold is None


def test_a_systemd_inhibit_that_takes_its_lock_after_a_slow_start_is_the_running_hold(
    world: World,
) -> None:
    started = world.root / "tail-started"
    world.replace_fake("systemd-inhibit", SLOW_HOLDING_INHIBIT)
    (world.root / "bin" / "tail").write_text(_tail(started))
    (world.root / "bin" / "tail").chmod(0o755)

    hold = system.keep_awake("linux")
    try:
        assert hold is not None, "a lock that holds counted as none"
        assert started.exists(), "it returned before systemd-inhibit held the lock"
        assert hold.poll() is None, "the hold isn't running"
    finally:
        _end(hold)


def test_a_systemd_inhibit_that_neither_holds_nor_exits_is_ended_after_the_bound(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = world.root / "inhibit.pid"
    world.replace_fake("systemd-inhibit", _stuck_inhibit(pid_file))
    monkeypatch.setattr(system, "INHIBIT_WAIT", 0.2, raising=False)

    began = time.monotonic()
    hold = system.keep_awake("linux")
    took = time.monotonic() - began
    _end(hold)

    assert hold is None, "a systemd-inhibit that holds nothing counted as a hold"
    assert took < 5, f"the batch's start waited {took:.1f} s, past the bound"
    assert not system.is_running(int(pid_file.read_text())), "it was left running"


def test_the_failing_systemd_inhibit_isnt_run_ahead_of_the_call_it_checks(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran = world.root / "failing-inhibit-ran"
    monkeypatch.setattr(failure, "FAILING_INHIBIT", f'#!/bin/sh\necho ran >> "{ran}"\nexit 1\n')

    failure._failing_inhibit(world)

    assert not ran.exists(), "the failing fake ran before the call it checks"
