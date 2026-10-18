"""Stands in for the `gh` CLI in tests, keeping GitHub's state in a JSON file."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

State = dict[str, Any]
Handler = Callable[[State, list[str], str], str]
URL = "https://github.com/owner/project"


def option(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def options(argv: list[str], name: str) -> list[str]:
    return [argv[index + 1] for index, arg in enumerate(argv) if arg == name]


def api_user(state: State, _argv: list[str], _stdin: str) -> str:
    return f"{state['login']}\n"


def issue_view(state: State, argv: list[str], _stdin: str) -> str:
    issue = state["issues"][argv[2]]
    return json.dumps(
        {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue["body"],
            "author": {"login": issue["author"]},
            "labels": [{"name": name} for name in issue["labels"]],
            "state": issue["state"],
        }
    )


def issue_edit(state: State, argv: list[str], _stdin: str) -> str:
    labels = state["issues"][argv[2]]["labels"]
    labels.extend(label for label in options(argv, "--add-label") if label not in labels)
    return ""


def issue_comment(state: State, argv: list[str], stdin: str) -> str:
    state["issues"][argv[2]]["comments"].append(stdin)
    return ""


def issue_create(state: State, argv: list[str], stdin: str) -> str:
    number = state["next"]
    state["next"] += 1
    state["issues"][str(number)] = {
        "number": number,
        "title": option(argv, "--title"),
        "body": stdin,
        "author": state["login"],
        "labels": options(argv, "--label"),
        "state": "OPEN",
        "comments": [],
    }
    return f"{URL}/issues/{number}\n"


def issue_list(state: State, argv: list[str], _stdin: str) -> str:
    label = option(argv, "--label")
    issues = state["issues"].values()
    return json.dumps(
        [
            {"number": issue["number"], "title": issue["title"]}
            for issue in issues
            if label in issue["labels"] and issue["state"] == "OPEN"
        ]
    )


def pr_list(state: State, argv: list[str], _stdin: str) -> str:
    wanted = [pr for pr in state["prs"].values() if pr["state"] == "OPEN"]
    if "--head" in argv:
        wanted = [pr for pr in wanted if pr["branch"] == option(argv, "--head")]
    if "--label" in argv:
        wanted = [pr for pr in wanted if option(argv, "--label") in pr["labels"]]
    return json.dumps([{"number": pr["number"], "title": pr["title"]} for pr in wanted])


def pr_create(state: State, argv: list[str], stdin: str) -> str:
    number = state["next"]
    state["next"] += 1
    branch = option(argv, "--head")
    state["prs"][str(number)] = {
        "number": number,
        "branch": branch,
        "base": option(argv, "--base"),
        "title": option(argv, "--title"),
        "body": stdin,
        "state": "OPEN",
        "labels": [],
        "comments": [],
        "armed": None,
        "views": state["pr_views"].pop(branch, []),
    }
    return f"{URL}/pull/{number}\n"


def pr_view(state: State, argv: list[str], _stdin: str) -> str:
    pr = state["prs"][argv[2]]
    merged = {"state": "MERGED" if pr["armed"] else "OPEN", "mergeable": "MERGEABLE"}
    view: dict[str, Any] = pr["views"].pop(0) if pr["views"] else merged
    if "push_conflict" in view:
        push_conflict(view["push_conflict"])
    pr["state"] = view["state"]
    return json.dumps(
        {
            "state": view["state"],
            "mergeable": view["mergeable"],
            "headRefOid": pr["armed"] or "",
            "statusCheckRollup": view.get("checks", []),
        }
    )


def pr_merge(state: State, argv: list[str], _stdin: str) -> str:
    state["prs"][argv[2]]["armed"] = option(argv, "--match-head-commit")
    return ""


def pr_edit(state: State, argv: list[str], _stdin: str) -> str:
    state["prs"][argv[2]]["labels"].extend(options(argv, "--add-label"))
    return ""


def pr_comment(state: State, argv: list[str], stdin: str) -> str:
    state["prs"][argv[2]]["comments"].append(stdin)
    return ""


def push_conflict(change: dict[str, str]) -> None:
    """Pushes a change to the base branch that conflicts with the PR, as another lane would."""
    with tempfile.TemporaryDirectory() as clone:
        git = ["git", "-C", clone]
        subprocess.run(["git", "clone", "--quiet", os.environ["FAKE_ORIGIN"], clone], check=True)
        (Path(clone) / change["file"]).write_text(change["content"])
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "--quiet", "-m", "another lane's change"], check=True)
        subprocess.run([*git, "push", "--quiet", "origin", "HEAD:master"], check=True)


HANDLERS: dict[tuple[str, str], Handler] = {
    ("api", "user"): api_user,
    ("issue", "view"): issue_view,
    ("issue", "edit"): issue_edit,
    ("issue", "comment"): issue_comment,
    ("issue", "create"): issue_create,
    ("issue", "list"): issue_list,
    ("pr", "list"): pr_list,
    ("pr", "create"): pr_create,
    ("pr", "view"): pr_view,
    ("pr", "merge"): pr_merge,
    ("pr", "edit"): pr_edit,
    ("pr", "comment"): pr_comment,
}


def main(argv: list[str]) -> int:
    if os.environ.get("FAKE_GH_DOWN"):
        print("error connecting to api.github.com", file=sys.stderr)
        return 1
    path = Path(os.environ["FAKE_GH_STATE"])
    stdin = sys.stdin.read() if "-" in argv else ""
    handler = HANDLERS.get((argv[0], argv[1])) if len(argv) > 1 else None
    with path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state: State = json.loads(path.read_text())
        state["calls"].append(argv)
        output = handler(state, argv, stdin) if handler is not None else None
        path.write_text(json.dumps(state))
    if output is None:
        print(f"the fake gh doesn't know {argv}", file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
