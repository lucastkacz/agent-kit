"""Each skill's frontmatter values are quoted, or plain YAML that a strict parser reads (#58).

`tests/test_skills.py` splits each line at its first colon, so it doesn't see a value that YAML
rejects, such as one holding `: `.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1] / "plugin"
SKILLS = sorted((PLUGIN / "skills").iterdir())
# Characters a YAML plain scalar can't start with.
INDICATORS = tuple("`@[]{}>|*&!%#")


def frontmatter_values(skill: Path) -> list[str]:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    head = text[4 : text.index("\n---\n", 4)]
    return [line.partition(":")[2].strip() for line in head.splitlines()]


@pytest.mark.parametrize("skill", SKILLS, ids=lambda path: path.name)
def test_each_frontmatter_value_is_quoted_or_valid_plain_yaml(skill: Path) -> None:
    for value in frontmatter_values(skill):
        if value[:1] in {'"', "'"}:
            continue
        assert ": " not in value, f"{skill.name}: quote or rephrase {value!r}"
        assert " #" not in value, f"{skill.name}: quote or rephrase {value!r}"
        assert not value.startswith(INDICATORS), f"{skill.name}: quote {value!r}"
