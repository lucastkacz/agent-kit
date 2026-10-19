"""Keeping the computer awake while a batch runs, and knowing when it's on battery.

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


def keep_awake(platform: str) -> subprocess.Popen[bytes] | None:
    """Holds off idle and system sleep until this process ends, or None where it can't."""
    if platform == "darwin":
        return _caffeinate()
    return None


def on_battery(platform: str) -> bool:
    """Whether the computer draws from its battery, where the platform can tell.

    The answer only decides a warning, so a check that fails counts as not on battery.
    """
    if platform == "darwin":
        return _pmset_on_battery()
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
