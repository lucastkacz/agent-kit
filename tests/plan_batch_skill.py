"""What tests of the `plan-batch` skill share: its text, its numbered sections, its merges."""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "plan-batch"


def text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def section(number: int) -> str:
    """The skill's `## <number>.` section, up to the next one."""
    return text().split(f"\n## {number}. ", 1)[1].split("\n## ", 1)[0]


def merge_step() -> str:
    """Step 6.1 of the skill: the merges."""
    return section(6).split("\n1. ", 1)[1].split("\n2. ", 1)[0]
