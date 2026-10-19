"""The runner's settings and their defaults."""

from __future__ import annotations

from dataclasses import dataclass

READY = "ready"
BLOCKED = "blocked"
BATCH = "batch"
HIGH_RISK = "risk:high"
# The lanes' worktrees: `<state_dir>/worktrees/lane-<n>`, and on macOS
# `<state_dir>/worktrees.noindex/lane-<n>`: Spotlight skips a folder whose name ends in `.noindex`,
# so it doesn't index each lane's thousands of new files (#198).
WORKTREES = "worktrees"
UNINDEXED_WORKTREES = "worktrees.noindex"
LANE_FOLDERS = (WORKTREES, UNINDEXED_WORKTREES)
LANE = "lane-"


def worktrees_folder(platform: str) -> str:
    """The folder, in the state folder, that holds the lanes' worktrees on this platform."""
    return UNINDEXED_WORKTREES if platform == "darwin" else WORKTREES


@dataclass(frozen=True)
class Config:
    base_branch: str = "master"
    remote: str = "origin"
    state_dir: str = ".agent-batch"
    lanes: int = 2
    issues_per_session: int = 3
    review_rounds: int = 2
    implement_timeout: float = 3600
    review_timeout: float = 1200
    merge_timeout: float = 1800
    poll_seconds: float = 30
    screen: bool = False
    worktrees: str = WORKTREES

    @property
    def upstream(self) -> str:
        return f"{self.remote}/{self.base_branch}"
