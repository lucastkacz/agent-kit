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
# One that neither takes its lock nor exits, as when the system bus never answers. It stays the
# fake, not a `sleep` it execs, so a process left behind still names the fake's path.
STUCK_INHIBIT = """#!/bin/sh
while :; do sleep 0.1; done
"""


def _slow_holding_inhibit(held: Path) -> str:
    """`systemd-inhibit` runs its command, what follows its flags, once it holds the lock."""
    return f"""#!/bin/sh
sleep 1
while [ "${{1#--}}" != "$1" ]; do shift; done
touch "{held}"
exec "$@"
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
    held = world.root / "inhibit-held"
    world.replace_fake("systemd-inhibit", _slow_holding_inhibit(held))

    hold = system.keep_awake("linux")
    try:
        assert hold is not None, "a lock that holds counted as none"
        assert held.exists(), "it returned before systemd-inhibit held the lock"
        assert hold.poll() is None, "the hold isn't running"
    finally:
        _end(hold)


def test_a_systemd_inhibit_that_neither_holds_nor_exits_is_ended_after_the_bound(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.replace_fake("systemd-inhibit", STUCK_INHIBIT)
    monkeypatch.setattr(system, "INHIBIT_WAIT", 0.2, raising=False)

    began = time.monotonic()
    hold = system.keep_awake("linux")
    took = time.monotonic() - began
    _end(hold)

    assert hold is None, "a systemd-inhibit that holds nothing counted as a hold"
    assert took < 5, f"the batch's start waited {took:.1f} s, past the bound"
    fake = str(world.root / "bin" / "systemd-inhibit")
    left = subprocess.run(["pgrep", "-f", fake], capture_output=True, text=True, check=False)
    assert left.stdout == "", "it was left running"


def test_the_failing_systemd_inhibit_isnt_run_ahead_of_the_call_it_checks(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran = world.root / "failing-inhibit-ran"
    monkeypatch.setattr(failure, "FAILING_INHIBIT", f'#!/bin/sh\necho ran >> "{ran}"\nexit 1\n')

    failure._failing_inhibit(world)

    assert not ran.exists(), "the failing fake ran before the call it checks"
