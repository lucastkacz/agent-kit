"""`agent-batch`: runs a batch or ships an issue, shows what runs, cleans branches, reads GitHub."""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from agent_batch.batch import Computer, Limits, run_batch
from agent_batch.clean import clean_branches
from agent_batch.context import Context
from agent_batch.core import denial_log, gh_read, progress
from agent_batch.core.config import Config, worktrees_folder
from agent_batch.core.env import clean_env
from agent_batch.core.plan import EFFORTS, MODEL_NAME, PlanError
from agent_batch.shell import checkout, proc, status
from agent_batch.shell.claude import Claude
from agent_batch.shell.events import EventLog
from agent_batch.shell.git import Git
from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from agent_batch.shell.status import StatusBoard
from agent_batch.shell.system import keep_awake, on_battery
from agent_batch.ship import ShipError, ship

SCREEN_ENV = "AGENT_BATCH_SCREEN"
POLL_ENV = "AGENT_BATCH_POLL_SECONDS"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            return _run(args)
        if args.command == "gh-read":
            return _gh_read(args.args)
        if args.command == "status":
            return _status_line() if args.line else _status()
        if args.command == "clean":
            return _clean()
        return _ship(args)
    except (CommandError, PlanError, ShipError, gh_read.Refused, SettingError) as error:
        sys.stderr.write(f"agent-batch: {error}\n")
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-batch", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run the batch of a tracking issue")
    run.add_argument("batch", type=int, help="the batch's tracking issue")
    run.add_argument(
        "--lanes",
        type=_at_least_one,
        help=f"lanes that run at a time (default: the batch issue's, else {Config.lanes})",
    )
    run.add_argument("--max-issues", type=_at_least_one, help="issues the batch may start")
    run.add_argument("--max-hours", type=_above_zero, help="hours after which no issue starts")
    run.add_argument("--screen", action="store_true", help="allow checks that take the screen")
    _model_flags(run, "the batch issue's")
    direct = commands.add_parser("ship", help="review the current branch and open its PR")
    direct.add_argument("issue", type=int, help="the issue the branch resolves")
    direct.add_argument("--title", required=True, help="the PR title, in Conventional Commits")
    direct.add_argument("--body-file", type=Path, required=True, help="the PR body")
    _model_flags(direct, "claude's own")
    shown = commands.add_parser(
        "status", help="show what each lane of a batch, and each ship, is doing"
    )
    shown.add_argument(
        "--line",
        action="store_true",
        help=(
            "in one short line, for Claude Code's status line: reads the session's JSON "
            "from stdin, to its end, unless stdin is a terminal"
        ),
    )
    commands.add_parser("clean", help="delete the local branches whose PR merged at their head")
    read = commands.add_parser("gh-read", help="run one of gh's reads of pull requests or the API")
    read.add_argument(
        "args", nargs=argparse.REMAINDER, help="pr view|list|diff|checks ..., or api <endpoint> ..."
    )
    return parser


def _model_flags(parser: argparse.ArgumentParser, default: str) -> None:
    parser.add_argument("--model", type=_model, help=f"the runs' model (default: {default})")
    parser.add_argument("--effort", choices=EFFORTS, help=f"the runs' effort (default: {default})")


def _model(text: str) -> str:
    if not MODEL_NAME.fullmatch(text):
        raise argparse.ArgumentTypeError(f"needs a model, such as opus, not {text!r}")
    return text


def _at_least_one(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"needs a whole number of at least 1, not {text!r}")
    return int(text)


class SettingError(Exception):
    """An environment variable holds a value the runner can't use."""


def _above_zero(text: str) -> float:
    number = _number_above_zero(text)
    if number is None:
        raise argparse.ArgumentTypeError(f"needs a number above 0, not {text!r}")
    return number


def _number_above_zero(text: str) -> float | None:
    try:
        number = float(text)
    except ValueError:
        return None
    # Rather than `number <= 0`, which lets "nan" through.
    return number if number > 0 else None


def _run(args: argparse.Namespace) -> int:
    ctx = _context(Path.cwd(), _config(screen=args.screen), f"batch-{args.batch}")
    awake = keep_awake(sys.platform)
    try:
        limits = Limits(args.max_issues, args.max_hours, args.lanes, args.model, args.effort)
        computer = Computer(
            kept_awake=awake is not None,
            on_battery=on_battery(sys.platform),
            # Not `os.process_cpu_count`: the owner's computer gives the runner all its cores, and
            # the acceptance tests of #198 set the cores through `os.cpu_count`.
            cores=os.cpu_count(),
        )
        return run_batch(ctx, args.batch, limits, computer)
    finally:
        if awake is not None:
            awake.terminate()
            awake.wait()


def _ship(args: argparse.Namespace) -> int:
    body = Path(args.body_file).read_text(encoding="utf-8")
    ctx = _context(Path.cwd(), _config(), f"ship-{args.issue}")
    ctx = replace(ctx, claude=ctx.claude.with_model(args.model, args.effort))
    return ship(ctx, Path.cwd(), args.issue, args.title, body)


def _status() -> int:
    """Prints a row per lane of the running batches and `agent-batch ship` runs (#107)."""
    config = Config()
    repo = Git(config).main_root(Path.cwd())
    rows = status.running(repo / config.state_dir)
    sys.stdout.write(progress.render(rows, time.time()))
    return 0


def _status_line() -> int:
    """The same in one line, for the plugin's status line (#108): it reads files, and runs nothing.

    The session's folder comes in Claude Code's JSON on stdin; typed by hand, it's this one.
    Outside a project that enables agent-kit, it prints nothing, so the mod shows no line (#171).
    """
    given = None if sys.stdin.isatty() else progress.session_cwd(sys.stdin.read())
    found = checkout.find(Path(given) if given else Path.cwd())
    # A folder outside any repository can't enable agent-kit either: the hooks don't act there.
    if found is None or not checkout.enabled_here(found.root):
        return 0
    rows = status.running(found.root / Config().state_dir)
    sys.stdout.write(progress.line(rows, time.time(), found.branch))
    return 0


def _clean() -> int:
    clean_branches(_context(Path.cwd(), _config(), "clean"))
    return 0


def _gh_read(args: Sequence[str]) -> int:
    """Runs the read with the caller's own `gh`, and passes on what it printed and its exit code."""
    done = proc.run(gh_read.command(args), Path.cwd())
    sys.stdout.write(done.out)
    sys.stderr.write(done.err)
    return done.code


def _config(*, screen: bool = False) -> Config:
    config = Config(screen=screen, worktrees=worktrees_folder(sys.platform))
    poll = os.environ.get(POLL_ENV)
    if not poll:
        return config
    seconds = _number_above_zero(poll)
    if seconds is None:
        raise SettingError(f"{POLL_ENV} needs a number above 0, not {poll!r}")
    return replace(config, poll_seconds=seconds)


def _context(cwd: Path, config: Config, log_name: str) -> Context:
    git = Git(config)
    repo = git.main_root(cwd)
    gh = GitHub(repo)
    env = clean_env(os.environ)
    if config.screen:
        env[SCREEN_ENV] = "1"
    folder = repo / config.state_dir / log_name
    events = EventLog(folder / "events.jsonl")
    # Only this batch's own log: its earlier runs, as when it's resumed (#156).
    spent = progress.earlier_rate(events.records("reviewed"))
    return Context(
        repo=repo,
        owner=gh.login(),
        config=config,
        git=git,
        gh=gh,
        claude=Claude(env, config, denials=repo / config.state_dir / denial_log.LOG),
        events=events,
        status=StatusBoard(folder / status.STATUS, os.getpid(), spent),
        # The wall clock: a monotonic clock can stop while the computer sleeps, as
        # `time.monotonic` does on macOS and Linux (#28).
        clock=time.time,
    )
