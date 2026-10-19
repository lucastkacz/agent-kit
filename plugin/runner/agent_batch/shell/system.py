"""Keeping the computer awake during a batch, knowing when it can't, and if a runner still runs.

One adapter per platform: `caffeinate` and `pmset` on macOS, `systemd-inhibit` and the kernel's
power supplies on Linux. Elsewhere, or without the tool, the batch can't keep the computer awake.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

PMSET_TIMEOUT = 10
POWER_SUPPLIES = Path("/sys/class/power_supply")
INHIBIT_WHY = "agent-batch is running a batch"
# `systemd-inhibit` that can't take its lock (no system bus, or polkit says no) exits at once.
INHIBIT_GRACE = 0.5


def keep_awake(platform: str) -> subprocess.Popen[bytes] | None:
    """Holds off idle and system sleep until this process ends, or None where it can't."""
    if platform == "darwin":
        return _caffeinate()
    if platform == "linux":
        return _systemd_inhibit()
    return None


def on_battery(platform: str) -> bool:
    """Whether the computer draws from its battery, where the platform can tell.

    The answer only decides a warning, so a check that fails counts as not on battery.
    """
    if platform == "darwin":
        return _pmset_on_battery()
    if platform == "linux":
        return _power_supplies_on_battery(POWER_SUPPLIES)
    return False


def _caffeinate() -> subprocess.Popen[bytes] | None:
    """`caffeinate` on macOS, which exits with this process.

    macOS holds off system sleep only on AC power, and closing the lid sleeps it anyway.
    """
    caffeinate = shutil.which("caffeinate")
    if caffeinate is None:
        return None
    return subprocess.Popen([caffeinate, "-i", "-s", "-w", str(os.getpid())])


def _pmset_on_battery() -> bool:
    """`pmset -g batt` on macOS; one that fails or hangs counts as not on battery."""
    pmset = shutil.which("pmset")
    if pmset is None:
        return False
    try:
        done = subprocess.run(
            [pmset, "-g", "batt"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=PMSET_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and "'Battery Power'" in done.stdout


def _systemd_inhibit() -> subprocess.Popen[bytes] | None:
    """`systemd-inhibit` on Linux, around a `tail` that exits with this process.

    Terminating `systemd-inhibit` ends the hold; its `tail` follows when this process ends.
    One that fails within `INHIBIT_GRACE` seconds holds nothing, so it counts as None.
    """
    inhibit, tail = shutil.which("systemd-inhibit"), shutil.which("tail")
    if inhibit is None or tail is None:
        return None
    awake = subprocess.Popen(
        [
            inhibit,
            "--what=idle:sleep",
            f"--why={INHIBIT_WHY}",
            "--mode=block",
            tail,
            f"--pid={os.getpid()}",
            "-f",
            "/dev/null",
        ]
    )
    try:
        failed = awake.wait(timeout=INHIBIT_GRACE) != 0
    except subprocess.TimeoutExpired:
        return awake
    return None if failed else awake


def _power_supplies_on_battery(supplies: Path) -> bool:
    """On Linux, on battery when the computer has a mains supply and none of them is online.

    A desktop may list no supply at all. A supply whose type can't be read is skipped, and a
    folder or a mains supply that can't be read counts as not on battery.
    """
    try:
        mains = [supply for supply in supplies.iterdir() if _kind(supply) == "Mains"]
        return bool(mains) and all(_read(supply / "online") == "0" for supply in mains)
    except OSError:
        return False


def _kind(supply: Path) -> str | None:
    try:
        return _read(supply / "type")
    except OSError:
        return None


def _read(path: Path) -> str:
    return path.read_text(encoding="ascii", errors="replace").strip()


def is_running(pid: int) -> bool:
    """Whether a process with this id still runs, so that a killed runner's state is left out."""
    if os.name != "posix":
        return True  # Elsewhere, `os.kill` with signal 0 would end the process instead.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # It runs, as another user.
    return True
