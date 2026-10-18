"""Headless Claude runs (SPEC §11.1): no prompts, structured answers, the subscription's billing."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from agent_batch.core import results
from agent_batch.core.config import Config
from agent_batch.core.model import ClaudeRun
from agent_batch.shell import proc

SETTINGS = Path(__file__).resolve().parent.parent / "data" / "batch-settings.json"

# The reviewer reads and runs the checks; it never edits, commits, pushes or writes to GitHub.
REVIEW_ALLOWED = (
    "Read", "Grep", "Glob", "Bash(git diff *)", "Bash(git log *)", "Bash(git show *)",
    "Bash(git status *)", "Bash(gh issue view *)", "Bash(make test)", "Bash(make check)",
)  # fmt: skip
REVIEW_DENIED = (
    "Edit", "Write", "NotebookEdit", "Bash(git commit *)", "Bash(git push *)", "Bash(gh pr *)",
    "Bash(gh issue edit *)", "Bash(gh issue comment *)", "Bash(gh issue create *)",
    "Bash(gh api *)",
)  # fmt: skip


class Claude:
    def __init__(self, env: Mapping[str, str], config: Config) -> None:
        self._env = env
        self._config = config

    def implement(self, cwd: Path, prompt: str, resume: str | None) -> ClaudeRun:
        """Runs the implementer, resuming the lane's session when there is one to resume."""
        options = ["--permission-mode", "auto"]
        run = self._run(cwd, prompt, [*options, *_resume(resume)], results.IMPLEMENT_SCHEMA)
        if resume is not None and run.data is None and not run.limit_reached:
            # A session that can't be resumed shouldn't cost the issue: start a fresh one.
            return self._run(cwd, prompt, options, results.IMPLEMENT_SCHEMA)
        return run

    def review(self, cwd: Path, prompt: str) -> ClaudeRun:
        options = [
            "--permission-mode", "dontAsk",
            "--allowedTools", *REVIEW_ALLOWED,
            "--disallowedTools", *REVIEW_DENIED,
        ]  # fmt: skip
        return self._run(cwd, prompt, options, results.REVIEW_SCHEMA, self._config.review_timeout)

    def resolve(self, cwd: Path, prompt: str) -> ClaudeRun:
        return self._run(cwd, prompt, ["--permission-mode", "auto"], results.RESOLVE_SCHEMA)

    def _run(
        self,
        cwd: Path,
        prompt: str,
        options: Sequence[str],
        schema: dict[str, object],
        timeout: float | None = None,
    ) -> ClaudeRun:
        limit = timeout if timeout is not None else self._config.implement_timeout
        args = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--json-schema", json.dumps(schema),
            "--permission-prompts", "none",
            "--settings", str(SETTINGS),
            *options,
        ]  # fmt: skip
        done = proc.run(args, cwd, env=self._env, timeout=limit)
        if done.timed_out:
            return ClaudeRun(None, None, f"the run took longer than {limit:.0f} seconds")
        if not done.out.strip():
            error = done.err.strip() or f"claude exited with code {done.code}"
            return ClaudeRun(None, None, error, limit_reached=bool(results.LIMIT.search(error)))
        return results.parse_run(done.out)


def _resume(session: str | None) -> list[str]:
    return ["--resume", session] if session is not None else []
