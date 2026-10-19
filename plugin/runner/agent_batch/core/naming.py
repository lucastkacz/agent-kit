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
# The markers of the block quotes and list items a line is in (CommonMark §5).
WITHIN = r"(?:[ \t]*(?:>|[-+*][ \t]|\d{1,9}[.)][ \t]))*[ \t]*"
# A fence's opening line (CommonMark §4.5): three or more backticks or tildes, after the markers of
# the block quotes and list items it's in. A backtick fence's info string has no backtick.
FENCE = re.compile(rf"(?P<within>{WITHIN})(?P<fence>`{{3,}}(?!.*`)|~{{3,}})")
# The block quotes' markers at the start of a line (CommonMark §5.1).
QUOTES = re.compile(r"(?:[ \t]*>[ ]?)*")
# A line that is a block of its own, so that no code span crosses its end: a heading, a thematic
# break or a setext heading's underline (CommonMark §4.1-4.3).
ALONE = re.compile(
    r" {0,3}(?:#{1,6}(?:[ \t]|$)|(?P<rule>[-*_])[ \t]*(?:(?P=rule)[ \t]*){2,}$|(?:=+|-+)[ \t]*$)"
)
# A line that ends the block before it, so that no code span crosses it: a blank line, a line of its
# own, or one that opens a block quote, a list item or a table's row (CommonMark §4-5, GFM tables).
BREAK = re.compile(rf"\s*$|{ALONE.pattern}| {{0,3}}(?:>|[-+*][ \t]|\d{{1,9}}[.)][ \t]|\|)")
# A code span (CommonMark §6.1): a run of backticks up to the next run as long, in one block.
# A run after a backslash opens none: the backslash escapes it.
CODE_SPAN = re.compile(r"(?<![`\\])(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)")


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
    body = _quote(body, [found for found in _read_by_github(body) if found[2] != own])
    # Read once quoted: a stray backtick can pair with an added one, and put `#N` in code. The
    # findings' references are quoted below.
    closes = any(found[2] == own for found in _read_by_github(body))
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


def _read_by_github(body: str) -> list[re.Match[str]]:
    """The body's closing references that GitHub reads: those out of code.

    One in code stays as written: GitHub doesn't read references there, and a backtick added inside
    a code span would break it. A URL can run on into a code span, and GitHub reads no reference cut
    by code either.
    """
    code = _code(body)
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
        quoted += f"{body[end : found.start(2)]}`{found[2]}`{space}"
        end = found.end()
    return quoted + body[end:]


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

    Close to CommonMark's blocks, enough to tell where code spans end. Where it can't tell, it errs
    toward text: a backtick too many shows, but a reference left out of code closes its issue.
    """
    lines = list(re.finditer(r".*\n?", body))
    start = index = 0
    while index < len(lines):
        line = lines[index]
        if opening := FENCE.match(line[0]):
            last = _fence_end(lines, index, opening)
            yield False, range(start, line.start())
            start, index = lines[last].end(), last + 1
            yield True, range(line.start(), start)
            continue
        if BREAK.match(line[0]):
            yield False, range(start, line.start())
            start = line.start()
        if ALONE.match(line[0]):
            yield False, range(start, line.end())
            start = line.end()
        index += 1
    yield False, range(start, len(body))


def _fence_end(lines: Sequence[re.Match[str]], index: int, opening: re.Match[str]) -> int:
    """The fence's last line: the one that closes it, or its opening line if it never closes.

    A fence that never closes may be one misread, so the lines after its opening one count as text.
    A fence in a block quote or a list item ends with it.
    """
    fence, within = opening["fence"], opening["within"]
    in_quotes = re.compile(rf"(?:[ \t]*>[ ]?){{{within.count('>')}}}")
    column = len(QUOTES.sub("", within, count=1))
    closing = re.compile(rf" {{0,3}}{fence}{fence[0]}*\s*")
    for later in range(index + 1, len(lines)):
        text = _within(lines[later][0], in_quotes, column)
        if text is None:
            return index
        if closing.fullmatch(text):
            return later
    return index


def _within(line: str, in_quotes: re.Pattern[str], column: int) -> str | None:
    """The line's text inside a fence's block quotes and list item, or None if it's out of them.

    A line is out of the block quotes without their `>` markers, and out of the list item when it's
    indented less than the item's text.
    """
    quoted = in_quotes.match(line)
    if not quoted:
        return None
    text = line[quoted.end() :]
    if not text.strip():
        # A blank line doesn't end a list item.
        return ""
    if len(text) - len(text.lstrip(" \t")) < column:
        return None
    return text[column:]
