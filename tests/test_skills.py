"""The plugin's skills are well formed, and the runner's prompts invoke skills that exist (#13).

`claude plugin validate` checks the manifests but not the skills' frontmatter, so this does.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent_batch.core import prompts

PLUGIN = Path(__file__).resolve().parents[1] / "plugin"
SKILLS = sorted((PLUGIN / "skills").iterdir())
# The frontmatter keys Claude Code documents for skills.
KNOWN_KEYS = frozenset(
    {
        "name", "description", "when_to_use", "argument-hint", "arguments",
        "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools",
        "model", "effort", "context", "agent", "hooks", "paths", "shell",
    }
)  # fmt: skip
SLASH = re.compile(r"^/([a-z0-9-]+):([a-z0-9-]+) ")


def frontmatter(skill: Path) -> dict[str, str]:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill.name}: SKILL.md starts without frontmatter"
    head = text[4 : text.index("\n---\n", 4)]
    fields: dict[str, str] = {}
    for line in head.splitlines():
        key, separator, value = line.partition(":")
        assert separator, f"{skill.name}: frontmatter line without a key: {line!r}"
        fields[key.strip()] = value.strip()
    return fields


@pytest.mark.parametrize("skill", SKILLS, ids=lambda path: path.name)
def test_each_skill_is_well_formed(skill: Path) -> None:
    fields = frontmatter(skill)
    assert fields.keys() <= KNOWN_KEYS, fields.keys() - KNOWN_KEYS
    assert fields.get("name") == skill.name
    assert fields.get("description")
    if "$ARGUMENTS" in (skill / "SKILL.md").read_text(encoding="utf-8"):
        assert fields.get("argument-hint"), f"{skill.name} takes arguments without a hint"


@pytest.mark.parametrize("prompt", [prompts.implement(7), prompts.review(7)])
def test_the_runners_prompts_invoke_skills_that_exist(prompt: str) -> None:
    match = SLASH.match(prompt)
    assert match is not None, prompt
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert match.group(1) == manifest["name"]
    assert (PLUGIN / "skills" / match.group(2) / "SKILL.md").is_file()


def implement_step(number: int) -> str:
    text = (PLUGIN / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
    start = text.index(f"\n## {number}. ")
    return text[start : text.index("\n## ", start + 1)]


def test_the_implement_skill_puts_later_tests_in_files_of_their_own() -> None:
    step = implement_step(2) + implement_step(3)
    assert "files of their own" in step, step
    assert "never in the acceptance tests' files" in step, step


def test_the_implement_skill_formats_the_acceptance_tests_before_their_commit() -> None:
    step = implement_step(2)
    assert "`make fmt`" in step, step
    assert step.index("`make fmt`") < step.index("Commit them on their own"), step
