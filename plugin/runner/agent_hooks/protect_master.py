"""A PreToolUse hook on Bash: no commits on `master`, and no pushes to it (SPEC §9.3).

GitHub's ruleset enforces the same on the server; this catches it before the command runs.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_hooks import log_denials
from agent_hooks.commands import GitCall, git_calls
from agent_hooks.repo import current_branch, project_root

PROTECTED = frozenset({"master", "main"})
WRITES = frozenset({"commit", "merge", "pull", "rebase", "reset", "cherry-pick", "revert", "am"})
FAST_FORWARDS = frozenset({"merge", "pull"})
FAST_FORWARD_MODES = frozenset({"--ff", "--no-ff", "--ff-only"})
EVERY_BRANCH = frozenset({"--all", "--mirror"})
PUSH_OPTIONS_WITH_VALUES = frozenset({"-o", "--push-option", "--repo", "--receive-pack", "--exec"})

BranchOf = Callable[[Path], str]


def refusal(call: GitCall, branch_of: BranchOf) -> str | None:
    """Why the git command may not run, or None when it may."""
    if call.subcommand in WRITES:
        branch = branch_of(call.directory)
        if branch in PROTECTED and not _fast_forward_only(call):
            hint = _fast_forward_hint(call.subcommand, branch)
            return (
                f"`git {call.subcommand}` on {branch}: work on a branch named "
                f"<issue>-<short-name>; changes reach {branch} only through a pull request.{hint}"
            )
        return None
    if call.subcommand == "push":
        target = _protected_target(call, branch_of)
        if target is not None:
            return f"`git push` to {target}: changes reach it only through a pull request."
    return None


def _fast_forward_hint(subcommand: str, branch: str) -> str:
    if subcommand == "merge":
        return f" To bring it up to date, `git merge --ff-only origin/{branch}` may run."
    if subcommand == "pull":
        return " To bring it up to date, use `git pull --ff-only`."
    return ""


def _fast_forward_only(call: GitCall) -> bool:
    """A merge or pull that may only fast-forward: it moves the branch and creates no commit.

    A pull's `--rebase` needs no rule of its own: with `--ff-only`, git refuses a diverged branch.
    """
    if call.subcommand not in FAST_FORWARDS:
        return False
    modes = [arg for arg in call.args if arg in FAST_FORWARD_MODES]
    # git obeys the last of them, so a later `--no-ff` undoes `--ff-only`.
    return modes[-1:] == ["--ff-only"]


def _protected_target(call: GitCall, branch_of: BranchOf) -> str | None:
    if EVERY_BRANCH.intersection(call.args):
        return "every branch, the protected ones included"
    refspecs = _positional(call.args)[1:]
    if not refspecs:
        branch = branch_of(call.directory)
        return branch if branch in PROTECTED else None
    for refspec in refspecs:
        destination = refspec.lstrip("+").rsplit(":", 1)[-1]
        if destination == "HEAD":
            destination = branch_of(call.directory)
        name = destination.removeprefix("refs/heads/")
        if name in PROTECTED:
            return name
    return None


def _positional(args: Sequence[str]) -> list[str]:
    words: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in PUSH_OPTIONS_WITH_VALUES:
            skip = True
        elif not arg.startswith("-"):
            words.append(arg)
    return words


def main() -> int:
    payload = json.load(sys.stdin)
    command = str(payload.get("tool_input", {}).get("command", ""))
    cwd = Path(payload.get("cwd") or ".")
    root = project_root(cwd)
    if root is None:
        return 0
    for call in git_calls(command, cwd):
        reason = refusal(call, current_branch)
        if reason is not None:
            _deny(root, payload, reason)
            return 0
    return 0


def _deny(root: Path, payload: dict[str, Any], reason: str) -> None:
    line = log_denials.entry(payload, f"protect-master blocked it: {reason}", datetime.now(UTC))
    # Claude Code ignores a hook that crashes, so a log it can't write mustn't let the call run.
    with suppress(OSError):
        log_denials.append(root, line)
    decision = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
    sys.stdout.write(json.dumps({"hookSpecificOutput": decision}))
