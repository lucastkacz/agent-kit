"""SPEC §9.2 says how the reviewer reads pull requests and the API, and why that's safe (#98).

These check the facts only; whether the wording reads well stays the owner's call.
"""

from __future__ import annotations

import re
from pathlib import Path

from agent_batch.core import gh_read

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def who_merges() -> str:
    """SPEC §9.2 in lowercase, on one line, so that a check doesn't depend on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("### 9.2 Who merges")
    end = text.index("\n### ", start + 1)
    return re.sub(r"\s+", " ", text[start:end]).lower()


def test_spec_9_2_says_the_reviewer_reads_through_gh_read_while_gh_pr_and_gh_api_stay_denied() -> (
    None
):
    section = who_merges()
    for token in ("reviewer", "`agent-batch gh-read`", "deny `gh pr` and `gh api`"):
        assert token in section, (token, section)


def test_spec_9_2_says_gh_read_runs_only_the_reads_and_get_api_calls() -> None:
    section = who_merges()
    for read in gh_read.PR_READS:
        assert f"`pr {read}`" in section, (read, section)
    assert "get `api` calls" in section, section


def test_spec_9_2_says_gh_read_refuses_methods_bodies_fields_and_graphql() -> None:
    section = who_merges()
    for token in ("refuses", "methods", "bodies", "fields", "graphql"):
        assert token in section, (token, section)
