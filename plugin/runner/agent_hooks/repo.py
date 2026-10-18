"""What the hooks ask git about the folder a session works in."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

SETTINGS = (".claude/settings.json", ".claude/settings.local.json")
PLUGIN = "agent-kit@"


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


def enabled_here(root: Path) -> bool:
    """Whether the project enables agent-kit in its own settings (SPEC §13).

    Installed for the user by mistake, the plugin would otherwise apply its rules to projects
    that follow others.
    """
    for name in SETTINGS:
        try:
            settings = json.loads((root / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        plugins = settings.get("enabledPlugins") if isinstance(settings, dict) else None
        if isinstance(plugins, dict) and any(
            key.startswith(PLUGIN) and value is True for key, value in plugins.items()
        ):
            return True
    return False


def project_root(directory: Path) -> Path | None:
    """The main checkout of a project that enables agent-kit, or None."""
    root = main_root(directory)
    return root if root is not None and enabled_here(root) else None
