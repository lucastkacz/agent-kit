"""The README names only what exists (#23), and its links reach their pages (#46)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A `[text](target)` link; targets with a scheme or an anchor alone are not local paths.
LINK = re.compile(r"\]\(([^)\s]+)\)")


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
