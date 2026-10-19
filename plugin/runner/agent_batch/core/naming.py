"""Branch names, PR titles and PR bodies (SPEC §14)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Sequence
from dataclasses import replace

from agent_batch.core import prompts
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
REFERENCE = r"(?:[\w.-]+/[\w.-]+)?#\d+|https://github\.com/\S+?/(?:issues|pull)/\d+"
CLOSING_REFERENCE = re.compile(rf"({CLOSING_KEYWORD}:?\s+)({REFERENCE})\b", re.IGNORECASE)
# A fenced code block's opening line (CommonMark §4.5): three or more backticks or tildes, indented
# by at most three spaces. A backtick fence's info string has no backtick.
FENCE = re.compile(r" {0,3}(`{3,}(?!.*`)|~{3,})")
# A heading is a block of one line: no code span crosses its end.
HEADING = re.compile(r" {0,3}#{1,6}(?:[ \t]|$)")
# A line that ends the block before it, so that no code span crosses it: a blank line, or one that
# opens a heading, a block quote, a list item or a table's row (CommonMark §4-5, GFM's tables).
BREAK = re.compile(rf"\s*$|{HEADING.pattern}| {{0,3}}(?:>|[-+*][ \t]|\d{{1,9}}[.)][ \t]|\|)")
# A code span (CommonMark §6.1): a run of backticks up to the next run as long, in one block.
# A run after a backslash opens none: the backslash escapes it.
CODE_SPAN = re.compile(r"(?<![`\\])(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)")


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
    """The body, then the review's findings, then `Closes #N` unless the body closes the issue.

    Only the issue closes on merge: every other closing reference goes in code.
    """
    closing = re.compile(rf"{CLOSING_KEYWORD} #{number}\b", re.IGNORECASE)
    # Whether the implementer's body closes the issue: the findings' references are quoted below.
    closes = closing.search(body) is not None
    body = _quote_others(body, number)
    if findings:
        listed = prompts.findings_list([_inert(finding) for finding in findings])
        body = f"{body.rstrip()}\n\n{FINDINGS_HEADING}\n\n{listed}\n".lstrip()
    if closes:
        return body
    return f"{body.rstrip()}\n\nCloses #{number}\n".lstrip()


def _inert(finding: Finding) -> Finding:
    """The finding, with each reference after a closing keyword in code, so the merge closes none.

    GitHub closes every issue a PR body names after a closing keyword, even in the reviewer's words,
    but it doesn't read references inside code.
    """

    def quote(text: str) -> str:
        return CLOSING_REFERENCE.sub(r"\1`\2`", text)

    return replace(finding, problem=quote(finding.problem), suggestion=quote(finding.suggestion))


def _quote_others(body: str, number: int) -> str:
    """The body, with every closing reference but the issue's own `#N` put in code.

    One already in code stays as written: GitHub doesn't read references there, and a backtick
    added inside a code span would break it.
    """
    code = _code(body)

    def quote(found: re.Match[str]) -> str:
        start, end = found.span()
        # A URL can run on into a code span, and GitHub reads no reference cut by code either.
        if found[2] == f"#{number}" or any(start < part.stop and part.start < end for part in code):
            return found[0]
        # A backtick right after would join the closing one, and move where the code spans end.
        space = " " if body.startswith("`", end) else ""
        return f"{found[1]}`{found[2]}`{space}"

    return CLOSING_REFERENCE.sub(quote, body)


def _code(body: str) -> list[range]:
    """Where the body is code: its fenced blocks, and the code spans in its other blocks."""
    code: list[range] = []
    for fenced, block in _blocks(body):
        if fenced:
            code.append(block)
        else:
            spans = CODE_SPAN.finditer(body, block.start, block.stop)
            code += [range(*span.span()) for span in spans]
    return code


def _blocks(body: str) -> Iterator[tuple[bool, range]]:
    """The body's blocks in order, each with whether it's fenced code.

    Close to CommonMark's blocks, enough to tell where code spans end. An open fence runs on to
    the end.
    """
    fence, start = "", 0
    for line in re.finditer(r".*\n?", body):
        if fence:
            if re.fullmatch(rf" {{0,3}}{fence}{fence[0]}*\s*", line[0]):
                yield True, range(start, line.end())
                fence, start = "", line.end()
        elif opening := FENCE.match(line[0]):
            yield False, range(start, line.start())
            fence, start = opening[1], line.start()
        elif BREAK.match(line[0]):
            yield False, range(start, line.start())
            start = line.start()
            if HEADING.match(line[0]):
                yield False, range(start, line.end())
                start = line.end()
    yield bool(fence), range(start, len(body))
