"""What tests of the `run-batch` skill share: its text, its cloud prompt, and their sections."""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "run-batch"
TRIAL = "Merge the waiting PRs on trial"


def skill_text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def prompt_text() -> str:
    return (SKILL / "cloud-prompt.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def step(text: str, number: int) -> str:
    start = text.index(f"\n{number}. ")
    end = text.find(f"\n{number + 1}. ", start)
    return text[start : end if end != -1 else len(text)]
