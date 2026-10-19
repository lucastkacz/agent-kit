"""The project and the branch of a folder, read off git's files alone (#108).

Claude Code's status line runs often: a `git` call there could wait on another one's lock.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_batch.core import project

GITDIR = "gitdir:"
BRANCH_REF = "ref: refs/heads/"
SHORT_SHA = 7


@dataclass(frozen=True)
class Checkout:
    """The main checkout's folder, and the branch of the working tree that holds the folder."""

    root: Path
    branch: str


def find(folder: Path) -> Checkout | None:
    """The checkout that holds `folder`, also from a worktree; None outside a repository."""
    for candidate in (folder, *folder.parents):
        dot_git = candidate / ".git"
        try:
            if dot_git.is_dir():
                return Checkout(candidate, _branch(dot_git))
            if dot_git.is_file():
                git_dir = _git_dir(dot_git)
                return Checkout(_common_dir(git_dir).parent, _branch(git_dir))
        except OSError:
            return None
    return None


def _git_dir(dot_git: Path) -> Path:
    """Where a worktree's `.git` file points: `gitdir: <main>/.git/worktrees/<name>`."""
    text = dot_git.read_text(encoding="utf-8").strip()
    if not text.startswith(GITDIR):
        raise OSError(f"{dot_git} doesn't say where its git folder is")
    return dot_git.parent / text.removeprefix(GITDIR).strip()


def _common_dir(git_dir: Path) -> Path:
    """The main checkout's `.git`, which a worktree's `commondir` file names."""
    common = git_dir / "commondir"
    if not common.is_file():
        return git_dir
    return (git_dir / common.read_text(encoding="utf-8").strip()).resolve()


def _branch(git_dir: Path) -> str:
    """The branch HEAD is on, or the start of its commit when it's on none."""
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith(BRANCH_REF):
        return head.removeprefix(BRANCH_REF)
    return head[:SHORT_SHA]


def enabled_here(root: Path) -> bool:
    """Whether the project at `root` enables agent-kit in its own settings (SPEC §13)."""
    for name in project.SETTINGS:
        try:
            text = (root / name).read_text(encoding="utf-8")
        except OSError:
            continue
        if project.enables_agent_kit(text):
            return True
    return False
