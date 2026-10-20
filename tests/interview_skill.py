"""What tests of the `interview` skill share: its folder, its text and its numbered sections."""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "interview"


def text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def section(number: int) -> str:
    """The skill's `## <number>.` section, up to the next one."""
    return text().split(f"\n## {number}. ", 1)[1].split("\n## ", 1)[0]
