"""Reading a pull request's state while its auto-merge is armed."""

from __future__ import annotations

from enum import StrEnum

from agent_batch.core.model import PrState

FAILED_CHECKS = frozenset(
    {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "ERROR"}
)


class MergeStatus(StrEnum):
    WAIT = "wait"
    MERGED = "merged"
    CLOSED = "closed"
    CONFLICT = "conflict"
    CHECKS_FAILED = "checks failed"
    TIMED_OUT = "timed out"


def decide(pr: PrState) -> MergeStatus:
    if pr.state == "MERGED":
        return MergeStatus.MERGED
    if pr.state == "CLOSED":
        return MergeStatus.CLOSED
    if pr.mergeable == "CONFLICTING":
        return MergeStatus.CONFLICT
    if FAILED_CHECKS.intersection(pr.checks):
        return MergeStatus.CHECKS_FAILED
    return MergeStatus.WAIT
