"""Keeping the computer awake while a batch runs."""

from __future__ import annotations

import os
import shutil
import subprocess


def keep_awake() -> subprocess.Popen[bytes] | None:
    """Holds off idle sleep until this process ends, where `caffeinate` exists (macOS)."""
    caffeinate = shutil.which("caffeinate")
    if caffeinate is None:
        return None
    return subprocess.Popen([caffeinate, "-i", "-w", str(os.getpid())])
