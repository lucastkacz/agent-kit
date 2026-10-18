"""Plain data shared by the runner's logic and its adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

ImplementStatus = Literal["done", "blocked", "failed"]
IssueKind = Literal["bug", "idea", "task"]


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
class FoundIssue:
    """Work an implementer found along the way, to become an issue of its own."""

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
    severity: str
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

    run: str
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
    denials: list[RunDenial] = field(default_factory=list[RunDenial])
    cost_usd: float = 0.0
    seconds: float = 0.0
    human_checks: int = 0
