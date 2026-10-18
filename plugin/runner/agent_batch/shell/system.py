"""Keeping the computer awake while a batch runs, and knowing when it can't."""

from __future__ import annotations

import os
import shutil
import subprocess


def keep_awake() -> subprocess.Popen[bytes] | None:
    """Holds off idle and system sleep until this process ends, where `caffeinate` exists (macOS).

    macOS holds off system sleep only on AC power, and closing the lid sleeps the Mac anyway.
    """
    caffeinate = shutil.which("caffeinate")
    if caffeinate is None:
        return None
    return subprocess.Popen([caffeinate, "-i", "-s", "-w", str(os.getpid())])


def on_battery() -> bool:
    """Whether the Mac draws from its battery, where `pmset` exists (macOS)."""
    pmset = shutil.which("pmset")
    if pmset is None:
        return False
    done = subprocess.run([pmset, "-g", "batt"], capture_output=True, text=True, check=False)
    return done.returncode == 0 and "'Battery Power'" in done.stdout
