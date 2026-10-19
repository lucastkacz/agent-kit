"""The real `claude -p` streams each tool use and ends in its result (contract test, #107).

`make contract` runs it, and records the stream that `tests/test_fakes_match_stream_recording.py`
compares the fake's with.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from support import make_project, record_stream

from agent_batch.core import progress, results
from agent_batch.core.env import clean_env
from agent_batch.shell import claude, proc

pytestmark = pytest.mark.contract

SMALL_MODEL = ("--model", "haiku")
TIMEOUT = 300
PROMPT = (
    "Read the file README.md. Then create a file named marker.txt that contains `hi`. Then answer "
    "with verdict `approved` and no findings."
)


def test_a_stream_shows_each_tool_use_as_it_goes_and_ends_in_the_runs_result(
    tmp_path: Path,
) -> None:
    project = make_project(tmp_path)
    command = claude.command(PROMPT, results.REVIEW_SCHEMA, [*claude.REVIEWER, *SMALL_MODEL])
    seen: list[str] = []
    root = str(project.resolve())

    done = proc.stream(
        command,
        project,
        clean_env(os.environ),
        TIMEOUT,
        lambda line: seen.extend(progress.actions(line, root)),
    )
    record_stream("claude-stream", done.out)

    assert "Read(README.md)" in seen
    assert results.ends_in_result(done.out)
    run = results.parse_run(done.out)
    assert run.error is None, run.error
    assert results.to_review(run.data or {}) is not None
    assert run.session_id
    assert run.cost_usd > 0
    assert len(run.denials) >= 1
    assert not (project / "marker.txt").exists()
