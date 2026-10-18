"""`agent-batch`: runs a batch, or ships one issue in direct mode."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from agent_batch.batch import Limits, run_batch
from agent_batch.context import Context
from agent_batch.core.config import Config
from agent_batch.core.env import clean_env
from agent_batch.core.plan import PlanError
from agent_batch.shell.claude import Claude
from agent_batch.shell.events import EventLog
from agent_batch.shell.git import Git
from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError
from agent_batch.shell.system import keep_awake
from agent_batch.ship import ShipError, ship

SCREEN_ENV = "AGENT_BATCH_SCREEN"
POLL_ENV = "AGENT_BATCH_POLL_SECONDS"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            return _run(args)
        return _ship(args)
    except (CommandError, PlanError, ShipError) as error:
        sys.stderr.write(f"agent-batch: {error}\n")
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-batch", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run the batch of a tracking issue")
    run.add_argument("batch", type=int, help="the batch's tracking issue")
    run.add_argument("--lanes", type=int, default=Config.lanes, help="lanes that run at a time")
    run.add_argument("--max-issues", type=int, help="issues the batch may start")
    run.add_argument("--max-hours", type=float, help="hours after which no issue starts")
    run.add_argument("--screen", action="store_true", help="allow checks that take the screen")
    direct = commands.add_parser("ship", help="review the current branch and open its PR")
    direct.add_argument("issue", type=int, help="the issue the branch resolves")
    direct.add_argument("--title", required=True, help="the PR title, in Conventional Commits")
    direct.add_argument("--body-file", type=Path, required=True, help="the PR body")
    return parser


def _run(args: argparse.Namespace) -> int:
    config = _config(lanes=args.lanes, screen=args.screen)
    ctx = _context(Path.cwd(), config, f"batch-{args.batch}")
    awake = keep_awake()
    try:
        return run_batch(ctx, args.batch, Limits(args.max_issues, args.max_hours))
    finally:
        if awake is not None:
            awake.terminate()
            awake.wait()


def _ship(args: argparse.Namespace) -> int:
    body = Path(args.body_file).read_text(encoding="utf-8")
    ctx = _context(Path.cwd(), _config(), f"ship-{args.issue}")
    return ship(ctx, Path.cwd(), args.issue, args.title, body)


def _config(lanes: int = Config.lanes, *, screen: bool = False) -> Config:
    poll = os.environ.get(POLL_ENV)
    return Config(
        lanes=lanes,
        screen=screen,
        poll_seconds=float(poll) if poll else Config.poll_seconds,
    )


def _context(cwd: Path, config: Config, log_name: str) -> Context:
    git = Git(config)
    repo = git.main_root(cwd)
    gh = GitHub(repo)
    env = clean_env(os.environ)
    if config.screen:
        env[SCREEN_ENV] = "1"
    return Context(
        repo=repo,
        owner=gh.login(),
        config=config,
        git=git,
        gh=gh,
        claude=Claude(env, config),
        events=EventLog(repo / config.state_dir / log_name / "events.jsonl"),
    )
