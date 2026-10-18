"""The repository list names only what exists, or says it's planned (#23), and links reach their
pages (#46)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USAGE = ROOT / "docs" / "usage.md"
# A `[text](target)` link; targets with a scheme or an anchor alone are not local paths.
LINK = re.compile(r"\]\(([^)\s]+)\)")
# The first `[text](path)` link or `` `code` `` span in an item names its path.
PATH = re.compile(r"\]\(([^)]+)\)|`([^`]+)`")
# An item marks its path as planned right after the bold name: "**`template/`**, planned: …".
PLANNED = re.compile(r"\*\*,\s*planned\b")


def repository_list() -> list[str]:
    """The bullet items of the usage page's "What's in the repository" section."""
    text = USAGE.read_text(encoding="utf-8")
    section = text.split("\n## What's in the repository\n", 1)[1].split("\n## ", 1)[0]
    return [line for line in section.splitlines() if line.startswith("- ")]


def test_the_repository_list_names_paths_that_exist_unless_planned() -> None:
    items = repository_list()
    assert items, 'docs/usage.md has no list under "What\'s in the repository"'
    for item in items:
        match = PATH.search(item)
        assert match is not None, f"docs/usage.md item names no path: {item!r}"
        if PLANNED.search(item):
            continue
        # A link is relative to the page; a code span names a path from the repository's root.
        path = USAGE.parent / match.group(1) if match.group(1) else ROOT / match.group(2)
        assert path.exists(), f"docs/usage.md names {path}, which doesn't exist: {item!r}"


def local_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    targets = [target.split("#", 1)[0] for target in LINK.findall(text)]
    return [target for target in targets if target and "://" not in target]


def test_the_readme_links_only_to_paths_that_exist() -> None:
    links = local_links(ROOT / "README.md")
    assert links, "README.md links to no page in the repository"
    for link in links:
        assert (ROOT / link).exists(), f"README links to {link}, which doesn't exist"


def test_the_usage_page_links_only_to_paths_that_exist() -> None:
    page = ROOT / "docs" / "usage.md"
    for link in local_links(page):
        assert (page.parent / link).exists(), f"docs/usage.md links to {link}, which doesn't exist"
