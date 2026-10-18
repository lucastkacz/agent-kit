"""The GitHub operations a batch needs, through the `gh` CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_batch.core.model import Issue, PrState
from agent_batch.shell import proc
from agent_batch.shell.proc import CommandError

# The fields the runner asks for; the contract tests record the real answers to them.
ISSUE_FIELDS = "number,title,body,author,labels,state"
PR_FIELDS = "state,mergeable,headRefOid,statusCheckRollup"


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

    def find_pr(self, branch: str) -> int | None:
        raw = self._json("pr", "list", "--head", branch, "--state", "open", "--json", "number")
        return int(raw[0]["number"]) if raw else None

    def create_pr(self, branch: str, base: str, title: str, body: str) -> int:
        url = self._gh(
            "pr", "create", "--base", base, "--head", branch, "--title", title, "--body-file", "-",
            stdin=body,
        )  # fmt: skip
        return _number(url)

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


def _number(url: str) -> int:
    last = url.strip().splitlines()[-1] if url.strip() else ""
    tail = last.rstrip("/").rsplit("/", 1)[-1]
    if not tail.isdigit():
        raise CommandError(f"gh didn't print an issue or PR URL: {url.strip()!r}")
    return int(tail)
