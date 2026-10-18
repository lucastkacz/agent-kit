"""What the hooks ask git about the folder a session works in."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git(directory: Path, *args: str) -> str | None:
    """git's output in that folder, or None when git fails there (not a repository, say)."""
    done = subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else None


def main_root(directory: Path) -> Path | None:
    """The main checkout's folder, also from inside a worktree."""
    common = git(directory, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent if common else None


def current_branch(directory: Path) -> str:
    return git(directory, "branch", "--show-current") or ""
