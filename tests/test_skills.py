"""The plugin's skills are well formed, and the runner's prompts invoke skills that exist (#13).

`claude plugin validate` checks the manifests but not the skills' frontmatter, so this does.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agent_batch.core import prompts
from skill_files import PLUGIN, check_well_formed, implement_step

SKILLS = sorted((PLUGIN / "skills").iterdir())
SLASH = re.compile(r"^/([a-z0-9-]+):([a-z0-9-]+) ")


@pytest.mark.parametrize("skill", SKILLS, ids=lambda path: path.name)
def test_each_skill_is_well_formed(skill: Path) -> None:
    check_well_formed(skill)


@pytest.mark.parametrize("prompt", [prompts.implement(7), prompts.review(7)])
def test_the_runners_prompts_invoke_skills_that_exist(prompt: str) -> None:
    match = SLASH.match(prompt)
    assert match is not None, prompt
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert match.group(1) == manifest["name"]
    assert (PLUGIN / "skills" / match.group(2) / "SKILL.md").is_file()


def test_the_implement_skill_puts_later_tests_in_files_of_their_own() -> None:
    step = implement_step(2) + implement_step(3)
    assert "files of their own" in step, step
    assert "never in the acceptance tests' files" in step, step


def test_the_implement_skill_formats_the_acceptance_tests_before_their_commit() -> None:
    step = implement_step(2)
    assert "`make fmt`" in step, step
    assert step.index("`make fmt`") < step.index("Commit them on their own"), step
