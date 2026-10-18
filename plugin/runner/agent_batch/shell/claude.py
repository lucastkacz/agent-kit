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

IMPLEMENTER = ("--permission-mode", "auto")
REVIEWER = (
    "--permission-mode", "dontAsk",
    "--allowedTools", *REVIEW_ALLOWED,
    "--disallowedTools", *REVIEW_DENIED,
)  # fmt: skip


def command(
    prompt: str,
    schema: dict[str, object],
    options: Sequence[str],
    *,
    model: str | None = None,
    effort: str | None = None,
) -> list[str]:
    """Every run's command line: one prompt, a JSON answer checked against a schema, no prompts.

    The prompt goes right after `-p`, and the model and effort before `options`, because the tool
    lists in `options` take every word after them.
    """
    return [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--permission-prompts", "none",
        "--settings", str(SETTINGS),
        *(["--model", model] if model is not None else []),
        *(["--effort", effort] if effort is not None else []),
        *options,
    ]  # fmt: skip


class Claude:
    def __init__(
        self,
        env: Mapping[str, str],
        config: Config,
        model: str | None = None,
        effort: str | None = None,
    ) -> None:
        self._env = env
        self._config = config
        self._model = model
        self._effort = effort

    def with_model(self, model: str | None, effort: str | None) -> Claude:
        """The same runs, on this model and effort (SPEC §11.1)."""
        return Claude(self._env, self._config, model, effort)

    def implement(self, cwd: Path, prompt: str, resume: str | None) -> ClaudeRun:
        """Runs the implementer, resuming the lane's session when there is one to resume."""
        options = [*IMPLEMENTER, *_resume(resume)]
        run = self._run(cwd, prompt, options, results.IMPLEMENT_SCHEMA)
        if resume is not None and run.data is None and not run.limit_reached:
            # A session that can't be resumed shouldn't cost the issue: start a fresh one.
            return self._run(cwd, prompt, IMPLEMENTER, results.IMPLEMENT_SCHEMA)
        return run

    def review(self, cwd: Path, prompt: str) -> ClaudeRun:
        timeout = self._config.review_timeout
        return self._run(cwd, prompt, REVIEWER, results.REVIEW_SCHEMA, timeout)

    def resolve(self, cwd: Path, prompt: str) -> ClaudeRun:
        return self._run(cwd, prompt, IMPLEMENTER, results.RESOLVE_SCHEMA)

    def _run(
        self,
        cwd: Path,
        prompt: str,
        options: Sequence[str],
        schema: dict[str, object],
        timeout: float | None = None,
    ) -> ClaudeRun:
        limit = timeout if timeout is not None else self._config.implement_timeout
        argv = command(prompt, schema, options, model=self._model, effort=self._effort)
        done = proc.run(argv, cwd, env=self._env, timeout=limit)
        if done.timed_out:
            return ClaudeRun(None, None, f"the run took longer than {limit:.0f} seconds")
        if not done.out.strip():
            error = done.err.strip() or f"claude exited with code {done.code}"
            return ClaudeRun(None, None, error, limit_reached=bool(results.LIMIT.search(error)))
        return results.parse_run(done.out)


def _resume(session: str | None) -> list[str]:
    return ["--resume", session] if session is not None else []
