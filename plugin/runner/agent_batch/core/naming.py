"""Branch names, PR titles and PR bodies (SPEC §14)."""

from __future__ import annotations

import re
import unicodedata

from agent_batch.core.model import Issue

MAX_SLUG = 40
MAX_TITLE = 72
COMMIT_TYPES = (
    "feat", "fix", "docs", "test", "refactor", "chore", "ci", "build", "perf", "style", "revert",
)  # fmt: skip
CONVENTIONAL_TITLE = re.compile(rf"^(?:{'|'.join(COMMIT_TYPES)})(?:\([a-z0-9-]+\))?!?: \S.*$")


def slugify(text: str) -> str:
    """Lowercase ASCII words joined by hyphens, cut at a word boundary."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    words: list[str] = re.findall(r"[a-z0-9]+", ascii_text.lower())
    slug = ""
    for word in words:
        candidate = f"{slug}-{word}" if slug else word
        if len(candidate) > MAX_SLUG:
            break
        slug = candidate
    if not slug and words:
        return words[0][:MAX_SLUG]
    return slug


def branch_name(issue: Issue) -> str:
    slug = slugify(issue.title)
    return f"{issue.number}-{slug}" if slug else str(issue.number)


def pr_title(proposed: str, issue: Issue) -> str:
    """The implementer's title if it follows Conventional Commits, or one built from the issue."""
    title = proposed.strip()
    if "\n" not in title and len(title) <= MAX_TITLE and CONVENTIONAL_TITLE.match(title):
        return title
    return f"{_default_type(issue)}: {issue.title.strip()}"


def _default_type(issue: Issue) -> str:
    if "bug" in issue.labels:
        return "fix"
    if "spike" in issue.labels:
        return "docs"
    return "feat"


def pr_body(body: str, number: int) -> str:
    """The body, with `Closes #N` added unless it already closes the issue."""
    closing = re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #{number}\b", re.IGNORECASE)
    if closing.search(body):
        return body
    return f"{body.rstrip()}\n\nCloses #{number}\n".lstrip()
