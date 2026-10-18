"""What every step of a batch works with."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_batch.core.config import Config
from agent_batch.shell.claude import Claude
from agent_batch.shell.events import EventLog
from agent_batch.shell.git import Git
from agent_batch.shell.github import GitHub


@dataclass(frozen=True)
class Context:
    repo: Path
    owner: str
    config: Config
    git: Git
    gh: GitHub
    claude: Claude
    events: EventLog


@dataclass
class Lane:
    """A lane's worktree, and the implementer session its issues share (SPEC §6)."""

    index: int
    worktree: Path
    session_id: str | None = None
    session_issues: int = 0
