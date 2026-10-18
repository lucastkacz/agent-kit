"""The real `claude -p` answers the way the runner reads it (contract tests).

Run them with `make contract`: they use the owner's subscription, with a small model, through the
runner's own command line.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from support import record

from agent_batch.core import results
from agent_batch.core.env import clean_env
from agent_batch.core.model import ClaudeRun
from agent_batch.shell import claude, proc

pytestmark = pytest.mark.contract

SMALL_MODEL = ("--model", "haiku")
TIMEOUT = 300
DONE = (
    "Don't use any tools. Answer with status `done`, title `feat: contract check`, pr_body "
    "`Contract check.`, an empty message and no found issues."
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    proc.must(["git", "init", "--quiet", "-b", "master"], tmp_path)
    (tmp_path / "README.md").write_text("A contract test's project.\n")
    proc.must(["git", "add", "-A"], tmp_path)
    proc.must(["git", "commit", "--quiet", "-m", "chore: start"], tmp_path)
    return tmp_path


def ask(
    project: Path, prompt: str, schema: dict[str, object], options: tuple[str, ...]
) -> tuple[str, ClaudeRun]:
    command = claude.command(prompt, schema, [*options, *SMALL_MODEL])
    done = proc.run(command, project, env=clean_env(os.environ), timeout=TIMEOUT)
    return done.out, results.parse_run(done.out)


def test_a_run_answers_with_structured_output_a_session_and_its_cost(project: Path) -> None:
    raw, run = ask(project, DONE, results.IMPLEMENT_SCHEMA, claude.IMPLEMENTER)
    record("claude-implement", raw)

    assert run.error is None, run.error
    work = results.to_implement(run.data or {})
    assert work is not None
    assert work.status == "done"
    assert run.session_id
    assert run.cost_usd >= 0


def test_a_session_resumes_from_the_same_folder(project: Path) -> None:
    _, first = ask(
        project, f"Remember the code word `pelican`. {DONE}", results.IMPLEMENT_SCHEMA,
        claude.IMPLEMENTER,
    )  # fmt: skip
    assert first.session_id

    recall = (
        "Don't use any tools. Answer with status `done`, title `chore: recall`, an empty "
        "pr_body, no found issues, and the code word I asked you to remember as the message."
    )
    resume = (*claude.IMPLEMENTER, "--resume", first.session_id)
    _, second = ask(project, recall, results.IMPLEMENT_SCHEMA, resume)

    work = results.to_implement(second.data or {})
    assert work is not None
    assert "pelican" in work.message.lower()


def test_the_reviewer_cant_write_and_its_denial_is_reported(project: Path) -> None:
    prompt = (
        "Create a file named marker.txt that contains `hi`. Then answer with verdict `approved` "
        "and no findings."
    )
    raw, run = ask(project, prompt, results.REVIEW_SCHEMA, claude.REVIEWER)
    record("claude-review", raw)

    assert not (project / "marker.txt").exists()
    assert run.denials >= 1


def test_the_batch_settings_deny_pushing(project: Path) -> None:
    prompt = (
        "Run exactly this shell command: `git push origin HEAD`. Then answer with status `done`, "
        "title `chore: push`, an empty pr_body, no found issues, and as the message whether the "
        "command ran."
    )
    _, run = ask(project, prompt, results.IMPLEMENT_SCHEMA, claude.IMPLEMENTER)

    assert run.denials >= 1
