"""A pull request's follow-up issue: the work found along the way, in one place (SPEC §4.5)."""

from __future__ import annotations

from collections.abc import Sequence

from agent_batch.core.model import FoundIssue, IssueKind


def label(items: Sequence[FoundIssue]) -> IssueKind:
    """The most severe kind among the items: a bug over a task over an idea."""
    raise NotImplementedError
