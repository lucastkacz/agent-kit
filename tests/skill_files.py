"""What tests of the plugin's skills share: reading a skill's frontmatter and its steps."""

from __future__ import annotations

from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugin"
# The frontmatter keys Claude Code documents for skills.
KNOWN_KEYS = frozenset(
    {
        "name", "description", "when_to_use", "argument-hint", "arguments",
        "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools",
        "model", "effort", "context", "agent", "hooks", "paths", "shell",
    }
)  # fmt: skip


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


def check_well_formed(skill: Path) -> None:
    fields = frontmatter(skill)
    assert fields.keys() <= KNOWN_KEYS, fields.keys() - KNOWN_KEYS
    assert fields.get("name") == skill.name
    assert fields.get("description")
    if "$ARGUMENTS" in (skill / "SKILL.md").read_text(encoding="utf-8"):
        assert fields.get("argument-hint"), f"{skill.name} takes arguments without a hint"


def implement_step(number: int) -> str:
    text = (PLUGIN / "skills" / "implement" / "SKILL.md").read_text(encoding="utf-8")
    start = text.index(f"\n## {number}. ")
    return text[start : text.index("\n## ", start + 1)]
