"""Headless Claude runs (SPEC §11.1): no prompts, structured answers, the subscription's billing."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from agent_batch.core import denial_log, progress, results
from agent_batch.core.config import Config
from agent_batch.core.model import ClaudeRun
from agent_batch.shell import proc

SETTINGS = Path(__file__).resolve().parent.parent / "data" / "batch-settings.json"
# Called with each tool use of a run, in short form, as the run goes (#107).
Watch = Callable[[str], None]
# Called with the tokens of each new message of a run, as the run goes (#144).
Count = Callable[[int], None]


@dataclass(frozen=True)
class Watcher:
    """Who follows a run as it goes: its tool uses, and its tokens."""

    act: Watch
    count: Count


# The reviewer reads and runs the checks; it never edits, commits, pushes or writes to GitHub.
# `gh pr` and `gh api` can write, so it reads pull requests and the API through `gh-read` (#72).
REVIEW_ALLOWED = (
    "Read", "Grep", "Glob", "Bash(git diff *)", "Bash(git log *)", "Bash(git show *)",
    "Bash(git status *)", "Bash(git ls-tree *)", "Bash(gh issue view *)",
    "Bash(gh issue list *)", "Bash(agent-batch gh-read *)", "Bash(make test)", "Bash(make check)",
)  # fmt: skip
REVIEW_DENIED = (
    "Edit", "Write", "NotebookEdit", "Bash(git commit *)", "Bash(git push *)", "Bash(gh pr *)",
    "Bash(gh issue edit *)", "Bash(gh issue comment *)", "Bash(gh issue create *)",
    "Bash(gh api *)",
)  # fmt: skip

# The implementer reads pull requests and the API through `gh-read` too, since the batch denies
# every run `gh pr` and `gh api` (#148).
IMPLEMENTER = ("--permission-mode", "auto", "--allowedTools", "Bash(agent-batch gh-read *)")
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
    lists in `options` take every word after them. The run prints each of its messages as it goes,
    which `-p` does only with `--verbose`, and ends with its result.
    """
    return [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--json-schema", json.dumps(schema),
        "--permission-prompts", "none",
        "--settings", str(SETTINGS),
        *(["--model", model] if model is not None else []),
        *(["--effort", effort] if effort is not None else []),
        *options,
    ]  # fmt: skip


class Claude:
    def __init__(self, env: Mapping[str, str], config: Config, denials: Path | None = None) -> None:
        self._env = env
        self._config = config
        # The PermissionDenied hook's log, whose entries of a run's session are its denials too.
        self._denials = denials
        self._model: str | None = None
        self._effort: str | None = None
        self._watcher: Watcher | None = None

    def with_model(self, model: str | None, effort: str | None) -> Claude:
        """The same runs, on this model and effort (SPEC §11.1)."""
        other = copy.copy(self)
        other._model, other._effort = model, effort
        return other

    def watching(self, watch: Watch, count: Count) -> Claude:
        """The same runs, handing `watch` each of their tool uses and `count` their tokens."""
        other = copy.copy(self)
        other._watcher = Watcher(watch, count)
        return other

    def implement(self, cwd: Path, prompt: str, resume: str | None) -> ClaudeRun:
        """Runs the implementer, resuming the lane's session when there is one to resume."""
        # The resume goes first: the tool list in IMPLEMENTER takes every word after it.
        options = [*_resume(resume), *IMPLEMENTER]
        run = self._run(cwd, prompt, options, results.IMPLEMENT_SCHEMA)
        if resume is not None and run.data is None and not run.limit_reached:
            # A session that can't be resumed shouldn't cost the issue: start a fresh one. Its
            # denials and cost still happened, so the fresh run's result carries them too.
            fresh = self._run(cwd, prompt, IMPLEMENTER, results.IMPLEMENT_SCHEMA)
            return replace(
                fresh, denials=run.denials + fresh.denials, cost_usd=run.cost_usd + fresh.cost_usd
            )
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
        start = _size(self._denials)
        done = proc.stream(argv, cwd, self._env, limit, self._follower(cwd))
        if done.timed_out:
            run = ClaudeRun(None, None, f"the run took longer than {limit:.0f} seconds")
        elif not results.ends_in_result(done.out):
            error = done.err.strip() or f"claude exited with code {done.code}"
            run = ClaudeRun(None, None, error, limit_reached=bool(results.LIMIT.search(error)))
        else:
            run = results.parse_run(done.out)
        return self._with_logged(run, run.session_id or results.stream_session(done.out), start)

    def _with_logged(self, run: ClaudeRun, session: str | None, start: int) -> ClaudeRun:
        """The run, with the denials the hook logged for its session since it started (#147).

        A run that ends without its result, as one that times out, still names its session in
        the stream's first message, and its denials count as well.
        """
        if self._denials is None or session is None:
            return run
        entries = denial_log.logged(_read_from(self._denials, start), session)
        return replace(run, denials=denial_log.combined(run.denials, entries, session))

    def _follower(self, cwd: Path) -> Callable[[str], None]:
        """Reads each line of the run's stream for its tool uses, with paths from its folder.

        And for its tokens: a message the stream repeats, once per block, counts once.
        """
        watcher = self._watcher
        if watcher is None:
            return _ignore
        # The tools name files by their real path, so a folder behind a link is resolved too.
        root = str(cwd.resolve())
        counted: set[str] = set()

        def follow(line: str) -> None:
            message = progress.usage(line)
            if message is not None and message[0] not in counted:
                counted.add(message[0])
                if message[1]:
                    watcher.count(message[1])
            for action in progress.actions(line, root):
                watcher.act(action)

        return follow


def _ignore(_line: str) -> None:
    """Follows a run that no one watches."""


def _size(path: Path | None) -> int:
    """Where the log ends now, so that a run reads only the entries written after it starts."""
    try:
        return path.stat().st_size if path is not None else 0
    except FileNotFoundError:
        return 0


def _read_from(path: Path, start: int) -> str:
    try:
        with path.open("rb") as log:
            log.seek(start)
            return log.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _resume(session: str | None) -> list[str]:
    return ["--resume", session] if session is not None else []
