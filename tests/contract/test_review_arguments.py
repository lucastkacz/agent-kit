"""The real `claude -p` hands the review skill its issue number and the earlier rounds (#104).

Run it with `make contract`. A re-review's prompt runs over several lines, and its findings hold
apostrophes and backticks, which the skill's shell-style argument splitting could misread.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from support import KIT, make_project

from agent_batch.core import prompts, results
from agent_batch.core.env import clean_env
from agent_batch.core.model import ClaudeRun, Denial, Finding
from agent_batch.core.rounds import Round
from agent_batch.shell import claude, proc

pytestmark = pytest.mark.contract

# A number that appears nowhere else in the prompt, so a command that names it got it from `$0`.
NUMBER = 8317
SMALL_MODEL = "haiku"
TIMEOUT = 600
ISSUE_VIEW = "Bash(gh issue view *)"


@pytest.fixture(scope="module")
def reviewed(tmp_path_factory: pytest.TempPathFactory) -> ClaudeRun:
    """One re-review, of a branch that left the earlier round's finding as it was."""
    project, head = _branch(tmp_path_factory.mktemp("review"))
    prompt = prompts.review(NUMBER, [_earlier_round(head)])
    later = prompt.split("\n", 1)[1]
    assert "'" in later
    assert "`" in later
    assert str(NUMBER) not in later
    command = claude.command(prompt, results.REVIEW_SCHEMA, _reviewer(), model=SMALL_MODEL)
    done = proc.run(command, project, env=clean_env(os.environ), timeout=TIMEOUT)
    return results.parse_run(done.out)


def test_the_review_skill_reads_the_issue_whose_number_the_prompt_gives(
    reviewed: ClaudeRun,
) -> None:
    views = [_command(denial) for denial in reviewed.denials]
    views = [view for view in views if view.startswith("gh issue view")]

    assert views, reviewed.denials
    for view in views:
        assert view.split()[3] == str(NUMBER), view
        assert "review" not in view.lower(), view
        assert "todo" not in view.lower(), view


def test_the_review_skill_gives_back_the_earlier_finding_the_branch_left(
    reviewed: ClaudeRun,
) -> None:
    review = results.to_review(reviewed.data or {})

    assert review is not None, reviewed.error
    earlier = [finding for finding in review.findings if finding.origin == "earlier"]
    assert any(finding.location.startswith("README.md") for finding in earlier), review


def _branch(folder: Path) -> tuple[Path, str]:
    """A project with an `origin`, and a branch whose one commit adds a TODO to the README."""
    project = folder / "project"
    project.mkdir()
    make_project(project)
    origin = folder / "origin.git"
    proc.must(["git", "init", "--quiet", "--bare", str(origin)], folder)
    proc.must(["git", "remote", "add", "origin", str(origin)], project)
    proc.must(["git", "push", "--quiet", "origin", "master"], project)
    proc.must(["git", "switch", "--quiet", "--create", "docs-install"], project)
    with (project / "README.md").open("a", encoding="utf-8") as readme:
        readme.write("TODO: say how to install it.\n")
    proc.must(["git", "commit", "--quiet", "-am", "docs: start the install section"], project)
    return project, proc.must(["git", "rev-parse", "HEAD"], project).strip()


def _earlier_round(head: str) -> Round:
    """The round that read the branch's commit, with a finding on its TODO, as real ones read."""
    finding = Finding(
        severity="low",
        origin="new",
        location="README.md:2",
        problem=(
            "The README's TODO isn't done: a user can't install the project, can they? It's the "
            "branch's only change.\nNothing says when `make install` gets written."
        ),
        suggestion="Write the install steps where the `TODO` is, or say why they wait.",
    )
    return Round(number=1, head=head, findings=(finding,))


def _reviewer() -> tuple[str, ...]:
    """The runner's reviewer, from the working tree's plugin, with `gh issue view` denied.

    The throwaway project doesn't enable agent-kit, so `--plugin-dir` loads the skill. A denied
    command comes back in the run's denials with the number the skill gave it. The reviewer's
    options end with its denied tools, so the last word adds one; `--plugin-dir` goes first,
    since the tool lists take every word after them.
    """
    assert "--disallowedTools" in claude.REVIEWER
    allowed = tuple(tool for tool in claude.REVIEWER if tool != ISSUE_VIEW)
    return ("--plugin-dir", str(KIT / "plugin"), *allowed, ISSUE_VIEW)


def _command(denial: Denial) -> str:
    command = denial.tool_input.get("command")
    return command.strip() if isinstance(command, str) else ""
