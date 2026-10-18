"""The README says what agent-kit does and what it's for; the technical details live apart (#46)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^```[ \t]*(\S*)", re.MULTILINE)
DOCS_LINK = re.compile(r"\]\((docs/[^)#\s]+\.md)\)")


def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def fence_languages(text: str) -> list[str]:
    """The info string of each opening fence; closing fences come in between and are skipped."""
    return FENCE.findall(text)[::2]


def test_the_readme_has_no_install_steps_or_command_lines() -> None:
    text = readme()
    code_blocks = [lang for lang in fence_languages(text) if lang != "mermaid"]
    assert code_blocks == [], f"README has code blocks other than diagrams: {code_blocks}"
    for command in ("claude plugin", "agent-batch run", "agent-batch ship"):
        assert command not in text, f"README gives the command {command!r}"


def test_the_readme_has_at_least_two_mermaid_diagrams() -> None:
    diagrams = [lang for lang in fence_languages(readme()) if lang == "mermaid"]
    assert len(diagrams) >= 2, f"README has {len(diagrams)} Mermaid diagrams, not at least 2"


def test_the_readme_links_to_a_usage_page_that_has_the_install_commands() -> None:
    links = DOCS_LINK.findall(readme())
    assert links, "README links to no page under docs/"
    pages = [ROOT / link for link in links if (ROOT / link).is_file()]
    assert pages, f"README links to {links}, and none of them exists"
    texts = [page.read_text(encoding="utf-8") for page in pages]
    assert any(
        "claude plugin marketplace add" in text and "claude plugin install" in text
        for text in texts
    ), f"None of {links} has the install commands"
