"""Running a command and reading what it printed."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

TIMED_OUT = 124


class CommandError(RuntimeError):
    """A command the runner depends on failed."""


@dataclass(frozen=True)
class Result:
    code: int
    out: str
    err: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.code == 0 and not self.timed_out


def run(
    args: Sequence[str],
    cwd: Path,
    env: Mapping[str, str] | None = None,
    stdin: str | None = None,
    timeout: float | None = None,
) -> Result:
    try:
        done = subprocess.run(
            list(args),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        return Result(TIMED_OUT, _text(expired.stdout), _text(expired.stderr), timed_out=True)
    except FileNotFoundError as missing:
        raise CommandError(f"{args[0]} isn't installed or isn't on the PATH") from missing
    return Result(done.returncode, done.stdout, done.stderr)


def must(args: Sequence[str], cwd: Path, stdin: str | None = None) -> str:
    """Runs the command and returns its output, or raises when it fails."""
    result = run(args, cwd, stdin=stdin)
    if not result.ok:
        message = result.err.strip() or result.out.strip() or f"exit code {result.code}"
        raise CommandError(f"`{' '.join(args[:3])}` failed: {message}")
    return result.out


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""
