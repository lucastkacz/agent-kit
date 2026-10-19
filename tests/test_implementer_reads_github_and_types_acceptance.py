"""The implementer reads GitHub through gh-read; its acceptance commit is typed and first (#148)."""

from __future__ import annotations

import re
from pathlib import Path

from agent_batch.shell import claude

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENT_SKILL = ROOT / "plugin" / "skills" / "implement" / "SKILL.md"
REVIEW_SKILL = ROOT / "plugin" / "skills" / "review" / "SKILL.md"
PROMPT = ROOT / "plugin" / "skills" / "run-batch" / "cloud-prompt.md"


def skill_tests_step() -> str:
    text = IMPLEMENT_SKILL.read_text(encoding="utf-8")
    start = text.index("## 2. Acceptance tests first")
    return text[start : text.index("\n## ", start + 1)]


def prompt_step_3() -> str:
    text = PROMPT.read_text(encoding="utf-8")
    start = text.index("\n3. Acceptance tests first")
    return text[start : text.index("\n4. ", start)]


def review_check_3() -> str:
    text = REVIEW_SKILL.read_text(encoding="utf-8")
    return next(line for line in text.splitlines() if "**Acceptance tests unchanged.**" in line)


def sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.;])\s+|\n", text)


def assert_types_the_acceptance_tests_before_committing(step: str) -> None:
    typed = [sentence for sentence in sentences(step) if "type checker" in sentence]
    assert typed, f"no sentence runs the type checker:\n{step}"
    assert any(
        "acceptance tests" in sentence
        and "read its output" in sentence
        and "before the acceptance commit" in sentence
        for sentence in typed
    ), typed


def test_the_implement_skill_reads_pull_requests_and_the_api_with_gh_read() -> None:
    text = IMPLEMENT_SKILL.read_text(encoding="utf-8")

    for command in (
        "agent-batch gh-read pr view",
        "agent-batch gh-read pr list",
        "agent-batch gh-read pr diff",
        "agent-batch gh-read pr checks",
        "agent-batch gh-read api",
    ):
        assert command in text, f"the implement skill doesn't name `{command}`"


def test_the_implement_skill_never_reads_with_gh_pr_or_gh_api() -> None:
    text = IMPLEMENT_SKILL.read_text(encoding="utf-8")
    line = next(line for line in text.splitlines() if "agent-batch gh-read" in line)

    assert "never" in line, line
    assert "`gh pr`" in line, line
    assert "`gh api`" in line, line


def test_the_implementer_is_allowed_gh_read_and_stays_in_auto_mode() -> None:
    line = claude.command("Work issue #1.", {}, claude.IMPLEMENTER)

    assert line[line.index("--permission-mode") + 1] == "auto"
    allowed = line[line.index("--allowedTools") + 1 :]
    assert "Bash(agent-batch gh-read *)" in allowed


def test_the_implement_skill_types_the_acceptance_tests_before_their_commit() -> None:
    assert_types_the_acceptance_tests_before_committing(skill_tests_step())


def test_the_cloud_prompt_types_the_acceptance_tests_before_their_commit() -> None:
    assert_types_the_acceptance_tests_before_committing(prompt_step_3())


def test_the_review_blocks_an_acceptance_commit_that_isnt_the_first_since_master() -> None:
    check = review_check_3()

    assert "first commit since master" in check, check
    assert "blocks" in check.split("first commit since master", 1)[1], check
