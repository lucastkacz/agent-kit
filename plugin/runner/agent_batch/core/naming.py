"""Branch names, PR titles and PR bodies (SPEC §14)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import replace

from agent_batch.core import markdown_code, prompts
from agent_batch.core.model import Finding, Issue

MAX_SLUG = 40
MAX_TITLE = 72
COMMIT_TYPES = (
    "feat", "fix", "docs", "test", "refactor", "chore", "ci", "build", "perf", "style", "revert",
)  # fmt: skip
CONVENTIONAL_TITLE = re.compile(rf"^(?:{'|'.join(COMMIT_TYPES)})(?:\([a-z0-9-]+\))?!?: \S.*$")
FINDINGS_HEADING = "## Review findings"
CLOSING_KEYWORD = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
# What GitHub closes on merge after a closing keyword: #N, owner/repo#N, or an issue's or PR's URL.
# A `#` escaped with a backslash still renders as one.
REFERENCE = r"(?:[\w.-]+/[\w.-]+)?\\?#\d+|https://github\.com/\S+?/(?:issues|pull)/\d+"
# The space between a keyword and its reference: a line break in a block quote takes the next line's
# `>` markers with it, since the rendered text has none.
SPACE = r"(?:[^\S\n]|\n(?:[ \t]*>)*)+"
CLOSING_REFERENCE = re.compile(rf"({CLOSING_KEYWORD}:?{SPACE})({REFERENCE})\b", re.IGNORECASE)
# The blank lines a PR body starts with. Only they go: the first line keeps its indentation, since
# four spaces make it code, and without them a line of backticks would open a fence.
LEADING_BLANK_LINES = re.compile(r"\A(?:[^\S\n]*\n)+")


def slugify(text: str) -> str:
    """Lowercase ASCII words joined by hyphens, cut at a word boundary."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    words: list[str] = re.findall(r"[a-z0-9]+", ascii_text.lower())
    return _whole_words(words, "-", MAX_SLUG)


def _whole_words(words: Sequence[str], separator: str, limit: int) -> str:
    """The words joined while they fit in `limit`, or the first word cut when not even it fits."""
    kept = ""
    for word in words:
        candidate = f"{kept}{separator}{word}" if kept else word
        if len(candidate) > limit:
            break
        kept = candidate
    if not kept and words:
        return words[0][:limit]
    return kept


def branch_name(issue: Issue) -> str:
    slug = slugify(issue.title)
    return f"{issue.number}-{slug}" if slug else str(issue.number)


def pr_title(proposed: str, issue: Issue) -> str:
    """The implementer's title if it follows Conventional Commits, or one built from the issue."""
    if title_refusal(proposed) is None:
        return proposed.strip()
    prefix = f"{_default_type(issue)}: "
    words = issue.title.strip().split(" ")
    return prefix + _whole_words(words, " ", MAX_TITLE - len(prefix)).rstrip()


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
    """The body, then the review's findings, then `Closes #N` unless the body closes the issue.

    Only the issue closes on merge: every other closing reference goes in code.
    """
    own = f"#{number}"
    if opening := markdown_code.open_fence(body):
        # Left open, the fence would run on over the findings and `Closes #N`. Closed before the
        # quoting, its lines are code, and their references stay as written.
        body = f"{body.rstrip()}\n{opening['within']}{opening['fence']}\n"
    others = _read_by_github(body, markdown_code.code(body))
    body = _quote(body, [found for found in others if _rendered(found) != own])
    # Read once closed and quoted: a stray backtick can pair with an added one, and put `#N` in
    # code. The findings' references are quoted below. The own reference errs toward code, and the
    # others toward text: a second `Closes #N` closes nothing more, but a reference misread as code
    # closes its issue, or, when it's the PR's own, leaves it open.
    code = [*markdown_code.code(body), *markdown_code.indented_code(body)]
    closes = any(_rendered(found) == own for found in _read_by_github(body, code))
    if findings:
        listed = prompts.findings_list([_inert(finding) for finding in findings])
        body = LEADING_BLANK_LINES.sub("", f"{body.rstrip()}\n\n{FINDINGS_HEADING}\n\n{listed}\n")
    if closes:
        return body
    return LEADING_BLANK_LINES.sub("", f"{body.rstrip()}\n\nCloses #{number}\n")


def _inert(finding: Finding) -> Finding:
    """The finding, with each reference after a closing keyword in code, so the merge closes none.

    GitHub closes every issue a PR body names after a closing keyword, even in the reviewer's words,
    but it doesn't read references inside code.
    """

    def quote(text: str) -> str:
        return CLOSING_REFERENCE.sub(lambda found: f"{found[1]}`{_rendered(found)}`", text)

    return replace(finding, problem=quote(finding.problem), suggestion=quote(finding.suggestion))


def _rendered(reference: re.Match[str]) -> str:
    """The reference as it renders: an escaped `#` loses its backslash, which code would show."""
    return reference[2].replace("\\#", "#")


def _read_by_github(body: str, code: Sequence[range]) -> list[re.Match[str]]:
    """The body's closing references that GitHub reads: those out of this code.

    One in code stays as written: GitHub doesn't read references there, and a backtick added inside
    a code span would break it. A URL can run on into a code span, and GitHub reads no reference cut
    by code either.
    """
    return [
        found
        for found in CLOSING_REFERENCE.finditer(body)
        if not any(found.start() < part.stop and part.start < found.end() for part in code)
    ]


def _quote(body: str, references: Sequence[re.Match[str]]) -> str:
    """The body, with these references in code, so the merge closes none of them."""
    quoted, end = "", 0
    for found in references:
        # A backtick right after would join the closing one, and move where the code spans end.
        space = " " if body.startswith("`", found.end()) else ""
        quoted += f"{body[end : found.start(2)]}`{_rendered(found)}`{space}"
        end = found.end()
    return quoted + body[end:]
