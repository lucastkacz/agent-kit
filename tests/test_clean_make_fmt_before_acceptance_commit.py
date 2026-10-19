"""An acceptance commit waits for a clean, read `make fmt`, and no lint rule is silenced (#110)."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "plugin" / "skills" / "run-batch" / "cloud-prompt.md"
SKILL = ROOT / "plugin" / "skills" / "implement" / "SKILL.md"
PYPROJECT = ROOT / "pyproject.toml"


def prompt_step_3() -> str:
    text = PROMPT.read_text(encoding="utf-8")
    start = text.index("\n3. Acceptance tests first")
    return text[start : text.index("\n4. ", start)]


def skill_tests_step() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## 2. Acceptance tests first")
    return text[start : text.index("\n## ", start + 1)]


def assert_a_clean_read_make_fmt(step: str) -> None:
    assert "`make fmt` must exit 0" in step, step
    assert "read its output, and never hide it" in step, step
    assert "fix by hand an error it can't fix before the acceptance commit" in step, step


def test_the_cloud_prompt_waits_for_a_clean_read_make_fmt() -> None:
    assert_a_clean_read_make_fmt(prompt_step_3())


def test_the_implement_skill_waits_for_a_clean_read_make_fmt() -> None:
    assert_a_clean_read_make_fmt(skill_tests_step())


def test_no_lint_rule_is_silenced_for_the_trusted_inputs_tests() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    ignores = config["tool"]["ruff"]["lint"]["per-file-ignores"]
    assert "tests/test_skill_plan_batch_trusted_inputs.py" not in ignores, ignores
