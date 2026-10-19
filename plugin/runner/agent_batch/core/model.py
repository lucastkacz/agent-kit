"""Plain data shared by the runner's logic and its adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

ImplementStatus = Literal["done", "blocked", "failed"]
IssueKind = Literal["bug", "idea", "task"]
RunKind = Literal["implementation", "review", "conflict resolution"]


class Outcome(StrEnum):
    """How an issue ended."""

    MERGED = "merged"
    ARMED = "auto-merge armed"
    WAITING_OWNER = "waiting for the owner"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEFERRED = "deferred"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    author: str
    labels: frozenset[str]
    state: str


@dataclass(frozen=True)
class Closure:
    """Why a closed issue was closed, and the PRs that close it."""

    reason: str
    prs: tuple[int, ...]


@dataclass(frozen=True)
class FoundIssue:
    """Work found along the way, one item of its PR's follow-up issue (SPEC §4.5)."""

    kind: IssueKind
    title: str
    body: str


@dataclass(frozen=True)
class ImplementResult:
    status: ImplementStatus
    title: str
    pr_body: str
    message: str
    found: tuple[FoundIssue, ...]


@dataclass(frozen=True)
class Finding:
    """A reviewer's finding; on a re-review, `origin` says whether an earlier round saw it."""

    severity: str
    origin: str
    location: str
    problem: str
    suggestion: str


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ResolveResult:
    resolved: bool
    message: str


@dataclass(frozen=True)
class Denial:
    """A tool call that the run's permissions refused."""

    tool: str
    tool_input: dict[str, object]


@dataclass(frozen=True)
class RunDenial:
    """A denial and the run it came from: implementation, review or conflict resolution."""

    run: RunKind
    denial: Denial


@dataclass(frozen=True)
class ClaudeRun:
    """What a headless Claude run returned, before its content is validated."""

    session_id: str | None
    data: dict[str, object] | None
    error: str | None
    denials: tuple[Denial, ...] = ()
    cost_usd: float = 0.0
    limit_reached: bool = False


@dataclass(frozen=True)
class PrState:
    state: str
    mergeable: str
    head_sha: str
    checks: tuple[str, ...]


@dataclass(frozen=True)
class MergedPr:
    """A merged PR, its branch, and the commit the branch ended at when it merged."""

    number: int
    branch: str
    head: str


@dataclass(frozen=True)
class LocalBranch:
    """A branch of the shared repository, and the worktree it's checked out in, if any."""

    name: str
    head: str
    worktree: Path | None = None
    main_folder: bool = False


@dataclass(frozen=True)
class Risk:
    high: bool
    reasons: tuple[str, ...]


@dataclass
class IssueReport:
    """What happened to one issue, for the batch's summary and numbers."""

    number: int
    outcome: Outcome
    detail: str = ""
    pr: int | None = None
    review_rounds: int = 0
    denials: list[RunDenial] = field(default_factory=list)
    cost_usd: float = 0.0
    seconds: float = 0.0
    human_checks: int = 0
    # The runner couldn't post its detail on GitHub, so only the batch's event log holds it.
    unannounced: bool = False
