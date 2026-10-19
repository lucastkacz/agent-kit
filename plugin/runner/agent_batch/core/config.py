"""The runner's settings and their defaults."""

from __future__ import annotations

from dataclasses import dataclass

READY = "ready"
BLOCKED = "blocked"
BATCH = "batch"
HIGH_RISK = "risk:high"
# The lanes' worktrees: `<state_dir>/worktrees/lane-<n>`.
WORKTREES = "worktrees"
LANE = "lane-"


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

    @property
    def upstream(self) -> str:
        return f"{self.remote}/{self.base_branch}"
