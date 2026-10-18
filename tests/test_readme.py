"""The README's top list names only what exists, or says it's planned (#23)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The first `[text](path)` link or `` `code` `` span in an item names its path.
PATH = re.compile(r"\]\(([^)]+)\)|`([^`]+)`")
# An item marks its path as planned right after the bold name: "**`template/`**, planned: …".
PLANNED = re.compile(r"\*\*,\s*planned\b")


def top_list() -> list[str]:
    """The bullet items between the title and the first section."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    head = text.split("\n## ", 1)[0]
    return [line for line in head.splitlines() if line.startswith("- ")]


def test_the_top_list_names_paths_that_exist_unless_planned() -> None:
    items = top_list()
    assert items, "README.md has no list under its title"
    for item in items:
        match = PATH.search(item)
        assert match is not None, f"README item names no path: {item!r}"
        path = match.group(1) or match.group(2)
        if PLANNED.search(item):
            continue
        assert (ROOT / path).exists(), f"README names {path}, which doesn't exist: {item!r}"
