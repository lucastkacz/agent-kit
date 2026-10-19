"""Running a command and reading what it printed."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO

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


def stream(
    args: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
    on_line: Callable[[str], None],
) -> Result:
    """Runs the command and hands `on_line` each line it prints, as it prints it.

    As `run` does, it waits for the output to end within `timeout`. Past it, the command is killed,
    without waiting for whatever it started that still holds the output open.
    """
    try:
        process = subprocess.Popen(
            list(args),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as missing:
        raise CommandError(f"{args[0]} isn't installed or isn't on the PATH") from missing
    out: list[str] = []
    err: list[str] = []

    def keep(line: str) -> None:
        out.append(line)
        on_line(line)

    readers = (_reader(process.stdout, keep), _reader(process.stderr, err.append))
    deadline = time.monotonic() + timeout
    if _ended(process, readers, deadline):
        return Result(process.returncode, "".join(out), "".join(err))
    process.kill()
    process.wait()
    return Result(TIMED_OUT, "".join(out), "".join(err), timed_out=True)


def _reader(pipe: IO[str] | None, keep: Callable[[str], None]) -> threading.Thread:
    """Reads the pipe to its end, and closes it there: only this thread ever touches it."""

    def read() -> None:
        if pipe is None:
            return
        with pipe:
            for line in pipe:
                keep(line)

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    return thread


def _ended(
    process: subprocess.Popen[str], readers: Sequence[threading.Thread], deadline: float
) -> bool:
    """Whether the output ended and the command exited before the deadline."""
    for reader in readers:
        reader.join(max(0.0, deadline - time.monotonic()))
        if reader.is_alive():
            return False
    try:
        process.wait(max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        return False
    return True


def must(args: Sequence[str], cwd: Path, stdin: str | None = None) -> str:
    """Runs the command and returns its output, or raises when it fails."""
    return output(args, run(args, cwd, stdin=stdin))


def output(args: Sequence[str], result: Result) -> str:
    """The command's output, or a `CommandError` that says why it failed."""
    if not result.ok:
        message = result.err.strip() or result.out.strip() or f"exit code {result.code}"
        raise CommandError(f"`{' '.join(args[:3])}` failed: {message}")
    return result.out


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""
