"""The GitHub operations a batch needs, through the `gh` CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_batch.core.model import Closure, Issue, MergedPr, PrState
from agent_batch.shell import proc
from agent_batch.shell.proc import CommandError

# The fields the runner asks for; the contract tests record the real answers to them.
ISSUE_FIELDS = "number,title,body,author,labels,state"
CLOSURE_FIELDS = "url,stateReason,closedByPullRequestsReferences"
PR_FIELDS = "state,mergeable,headRefOid,statusCheckRollup"
MERGED_PR_FIELDS = "number,headRefOid"


class GitHub:
    def __init__(self, cwd: Path) -> None:
        self._cwd = cwd

    def _gh(self, *args: str, stdin: str | None = None) -> str:
        return proc.must(["gh", *args], self._cwd, stdin=stdin)

    # gh prints JSON of many shapes; each caller reads the fields it asked for.
    def _json(self, *args: str) -> Any:
        return json.loads(self._gh(*args))

    def login(self) -> str:
        return self._gh("api", "user", "--jq", ".login").strip()

    def issue(self, number: int) -> Issue:
        raw = self._json("issue", "view", str(number), "--json", ISSUE_FIELDS)
        return Issue(
            number=int(raw["number"]),
            title=str(raw["title"]),
            body=str(raw["body"] or ""),
            author=str(raw["author"]["login"]),
            labels=frozenset(str(label["name"]) for label in raw["labels"]),
            state=str(raw["state"]),
        )

    def add_label(self, number: int, label: str) -> None:
        self._gh("issue", "edit", str(number), "--add-label", label)

    def comment(self, number: int, body: str) -> None:
        self._gh("issue", "comment", str(number), "--body-file", "-", stdin=body)

    def create_issue(self, title: str, body: str, label: str) -> int:
        url = self._gh(
            "issue", "create", "--title", title, "--body-file", "-", "--label", label, stdin=body
        )
        return _number(url)

    def closure(self, number: int) -> Closure:
        return closure_of(self._json("issue", "view", str(number), "--json", CLOSURE_FIELDS))

    def find_pr(self, branch: str) -> int | None:
        raw = self._json("pr", "list", "--head", branch, "--state", "open", "--json", "number")
        return int(raw[0]["number"]) if raw else None

    def merged_prs(self, branch: str) -> list[MergedPr]:
        """The branch's merged PRs, each with the head it merged at, kept after the merge."""
        raw = self._json(
            "pr", "list", "--head", branch, "--state", "merged", "--json", MERGED_PR_FIELDS
        )
        return [MergedPr(number=int(pr["number"]), head=str(pr["headRefOid"])) for pr in raw]

    def create_pr(self, branch: str, base: str, title: str, body: str) -> int:
        url = self._gh(
            "pr", "create", "--base", base, "--head", branch, "--title", title, "--body-file", "-",
            stdin=body,
        )  # fmt: skip
        return _number(url)

    def edit_pr(self, number: int, title: str, body: str) -> None:
        self._gh("pr", "edit", str(number), "--title", title, "--body-file", "-", stdin=body)

    def pr_state(self, number: int) -> PrState:
        raw = self._json("pr", "view", str(number), "--json", PR_FIELDS)
        checks = tuple(
            str(check.get("conclusion") or check.get("state") or check.get("status") or "").upper()
            for check in raw.get("statusCheckRollup") or []
        )
        return PrState(
            state=str(raw["state"]),
            mergeable=str(raw.get("mergeable") or "UNKNOWN"),
            head_sha=str(raw.get("headRefOid") or ""),
            checks=checks,
        )

    def arm_merge(self, number: int, sha: str) -> None:
        """Auto-merge, squashed, and only if the branch still ends at the reviewed commit."""
        self._gh("pr", "merge", str(number), "--auto", "--squash", "--match-head-commit", sha)

    def pr_add_label(self, number: int, label: str) -> None:
        self._gh("pr", "edit", str(number), "--add-label", label)

    def pr_comment(self, number: int, body: str) -> None:
        self._gh("pr", "comment", str(number), "--body-file", "-", stdin=body)


def closure_of(raw: Any) -> Closure:
    """The issue's close reason and the PRs that close it, from its own repository only.

    A PR of another repository can close the issue too, but its number means another PR here.
    """
    repository = str(raw["url"]).rsplit("/issues/", 1)[0]
    prs = tuple(
        int(pr["number"])
        for pr in raw.get("closedByPullRequestsReferences") or []
        if str(pr.get("url", "")).startswith(f"{repository}/pull/")
    )
    return Closure(reason=str(raw.get("stateReason") or ""), prs=prs)


def _number(url: str) -> int:
    last = url.strip().splitlines()[-1] if url.strip() else ""
    tail = last.rstrip("/").rsplit("/", 1)[-1]
    if not tail.isdigit():
        raise CommandError(f"gh didn't print an issue or PR URL: {url.strip()!r}")
    return int(tail)
