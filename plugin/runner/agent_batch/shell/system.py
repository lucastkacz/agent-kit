"""Keeping the computer awake while a batch runs, and knowing when it can't."""

from __future__ import annotations

import os
import shutil
import subprocess

PMSET_TIMEOUT = 10


def keep_awake() -> subprocess.Popen[bytes] | None:
    """Holds off idle and system sleep until this process ends, where `caffeinate` exists (macOS).

    macOS holds off system sleep only on AC power, and closing the lid sleeps the Mac anyway.
    """
    caffeinate = shutil.which("caffeinate")
    if caffeinate is None:
        return None
    return subprocess.Popen([caffeinate, "-i", "-s", "-w", str(os.getpid())])


def on_battery() -> bool:
    """Whether the Mac draws from its battery, where `pmset` exists (macOS).

    The answer only decides a warning, so a `pmset` that fails or hangs counts as not on battery.
    """
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
