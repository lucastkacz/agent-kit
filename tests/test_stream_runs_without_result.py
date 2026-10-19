"""A run whose stream ends without its result message reads its standard error, as before (#107).

A run that dies after some messages lands here, and so does a usage limit said only on stderr.
"""

from __future__ import annotations

import os

from agent_batch.core import prompts
from agent_batch.core.config import Config
from agent_batch.core.env import clean_env
from agent_batch.shell.claude import Claude
from conftest import World

READ = {"name": "Read", "input": {"file_path": "README.md"}}


def runner() -> Claude:
    return Claude(clean_env(os.environ), Config())


def test_a_usage_limit_said_only_on_stderr_stops_the_run_as_the_limit(world: World) -> None:
    world.script(
        "implement",
        10,
        {"tools": [READ], "raw": "", "stderr": "Claude usage limit reached.\n", "code": 1},
    )

    run = runner().implement(world.project, prompts.implement(10), None)

    assert run.data is None
    assert run.error == "Claude usage limit reached."
    assert run.limit_reached is True


def test_a_run_that_dies_mid_stream_reports_its_stderr(world: World) -> None:
    world.script("implement", 10, {"tools": [READ], "raw": "", "stderr": "Out of memory.\n"})

    run = runner().implement(world.project, prompts.implement(10), None)

    assert run.error == "Out of memory."
    assert run.limit_reached is False


def test_a_run_that_dies_mid_stream_without_a_word_reports_its_exit_code(world: World) -> None:
    world.script("review", 10, {"tools": [READ], "raw": "", "code": 3})

    run = runner().review(world.project, prompts.review(10))

    assert run.error == "claude exited with code 3"
    assert run.data is None
