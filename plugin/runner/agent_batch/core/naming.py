"""Branch names, PR titles and PR bodies (SPEC §14)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from agent_batch.core import prompts
from agent_batch.core.model import Finding, Issue

MAX_SLUG = 40
MAX_TITLE = 72
COMMIT_TYPES = (
    "feat", "fix", "docs", "test", "refactor", "chore", "ci", "build", "perf", "style", "revert",
)  # fmt: skip
CONVENTIONAL_TITLE = re.compile(rf"^(?:{'|'.join(COMMIT_TYPES)})(?:\([a-z0-9-]+\))?!?: \S.*$")
FINDINGS_HEADING = "## Review findings"


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
    if title_refusal(proposed) is None:
        return proposed.strip()
    return f"{_default_type(issue)}: {issue.title.strip()}"


def title_refusal(proposed: str) -> str | None:
    """Why `proposed` can't be a PR's title, or None when it can."""
    title = proposed.strip()
    if "\n" in title:
        return "it has more than one line"
    if len(title) > MAX_TITLE:
        return f"it has {len(title)} characters, and a title has at most {MAX_TITLE}"
    if not CONVENTIONAL_TITLE.match(title):
        return (
            "it doesn't follow Conventional Commits, `<type>: <summary>` with a type such as feat"
        )
    return None


def _default_type(issue: Issue) -> str:
    if "bug" in issue.labels:
        return "fix"
    if "spike" in issue.labels:
        return "docs"
    return "feat"


def pr_body(body: str, number: int, findings: Sequence[Finding] = ()) -> str:
    """The body, then the review's findings, then `Closes #N` unless the body closes the issue."""
    closing = re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #{number}\b", re.IGNORECASE)
    # Only the implementer's words count: a finding may quote "fixes #N" without closing anything.
    closes = closing.search(body) is not None
    if findings:
        listed = prompts.findings_list(findings)
        body = f"{body.rstrip()}\n\n{FINDINGS_HEADING}\n\n{listed}\n".lstrip()
    if closes:
        return body
    return f"{body.rstrip()}\n\nCloses #{number}\n".lstrip()
