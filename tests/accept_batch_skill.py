"""What tests of the `accept-batch` skill share: its text and its numbered sections."""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "accept-batch"


def text() -> str:
    assert (SKILL / "SKILL.md").is_file(), f"no skill at {SKILL}"
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def section(heading: str) -> str:
    """The skill's `## <n>. <heading>` section, up to the next `## `."""
    body = text()
    start = re.search(rf"^## \d+\. {re.escape(heading)}", body, re.MULTILINE)
    assert start is not None, f"no section `## <n>. {heading}`"
    end = body.find("\n## ", start.end())
    return re.sub(r"\s+", " ", body[start.start() : end if end != -1 else None]).lower()
