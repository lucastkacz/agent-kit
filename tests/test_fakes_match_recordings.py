"""The fakes answer in the shapes the real tools answered in the contract tests (small tests).

`make contract` records the real answers. When `gh` or `claude` change theirs, this test fails
until the fakes catch up.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fake_claude
import fake_gh
import pytest

RECORDED = Path(__file__).parent / "contract" / "recorded"
MISSING = object()
CLAUDE_FIELDS = (
    "type", "is_error", "result", "session_id", "total_cost_usd", "permission_denials",
    "structured_output",
)  # fmt: skip
# `gh pr list --state merged` answers a top-level list, which a leading `[]` reads.
MERGED_PR_LIST = ("[].number", "[].headRefName", "[].headRefOid")

# The fields the runner reads from each answer, in `shell/github.py` and `core/results.py`.
FIELDS: dict[str, tuple[str, ...]] = {
    "gh-issue-view": ("number", "title", "body", "author.login", "labels[].name", "state"),
    "gh-issue-closure": ("url", "stateReason", "closedByPullRequestsReferences"),
    "gh-pr-view": ("state", "mergeable", "headRefOid", "statusCheckRollup[].conclusion"),
    "claude-implement": CLAUDE_FIELDS,
    "claude-review": CLAUDE_FIELDS,
    "gh-pr-list-merged": MERGED_PR_LIST,
    "gh-pr-list-recent-merged": MERGED_PR_LIST,
}


def pluck(data: Any, path: str) -> Any:
    value = data
    for part in path.split("."):
        key, many = (part[:-2], True) if part.endswith("[]") else (part, False)
        if key:
            value = value.get(key, MISSING) if isinstance(value, dict) else MISSING
        if many:
            value = value[0] if isinstance(value, list) and value else MISSING
    return value


def kind(value: object) -> str:
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


def fake_answer(name: str) -> Any:
    if name in ("gh-issue-view", "gh-issue-closure"):
        issue = {"number": 7, "title": "t", "body": "b", "author": "owner", "labels": ["task"]}
        state = {"issues": {"7": {**issue, "state": "OPEN", "comments": []}}}
        return json.loads(fake_gh.issue_view(state, ["issue", "view", "7"], ""))
    if name == "gh-pr-view":
        view = {"state": "OPEN", "mergeable": "MERGEABLE", "checks": [{"conclusion": "FAILURE"}]}
        state = {"prs": {"8": {"armed": "abc", "state": "OPEN", "views": [view]}}}
        return json.loads(fake_gh.pr_view(state, ["pr", "view", "8"], ""))
    if name in ("gh-pr-list-merged", "gh-pr-list-recent-merged"):
        merged = {"number": 9, "title": "t", "branch": "9-b", "state": "MERGED", "head": "a" * 40}
        state = {"prs": {"9": merged}}
        return json.loads(fake_gh.pr_list(state, ["pr", "list", "--state", "merged"], ""))
    run_kind = "review" if name == "claude-review" else "implement"
    return fake_claude.result_json(run_kind, 7, {"denials": 1}, 0)


@pytest.mark.parametrize("name", sorted(FIELDS))
def test_the_fake_answers_like_the_real_tool(name: str) -> None:
    recorded = json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))
    fake = fake_answer(name)
    for field in FIELDS[name]:
        real = pluck(recorded, field)
        assert real is not MISSING, f"the real {name} has no {field}, which the runner reads"
        assert kind(pluck(fake, field)) == kind(real), f"{name}: {field}"
