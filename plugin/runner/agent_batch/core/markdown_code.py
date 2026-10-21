"""Where a PR body's Markdown is code, as GitHub renders it (CommonMark, GFM)."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

# The markers of the block quotes and list items a line is in (CommonMark §5).
WITHIN = r"(?:[ \t]*(?:>|[-+*][ \t]|\d{1,9}[.)][ \t]))*[ \t]*"
# A fence's opening line (CommonMark §4.5): three or more backticks or tildes, after the markers of
# the block quotes and list items it's in. A backtick fence's info string has no backtick.
FENCE = re.compile(rf"(?P<within>{WITHIN})(?P<fence>`{{3,}}(?!.*`)|~{{3,}})")
# What precedes a top-level fence: at most 3 spaces, since 4 make an indented code block.
TOP_LEVEL = re.compile(r" {0,3}")
# A list item's marker, up to where its text starts (CommonMark §5.2).
ITEM = re.compile(r" *(?:[-+*]|\d{1,9}[.)])(?:[ \t]+|$)")
# An ordered item numbered other than 1, which doesn't interrupt a paragraph.
ORDERED_NOT_ONE = re.compile(r" *(?!0*1[.)])\d")
# A line that opens a block quote.
QUOTE = re.compile(r" {0,3}>")
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
# The block quotes' markers at the start of a line whose tabs are expanded (CommonMark §5.1).
# Unlike QUOTES, it reads text with no tabs left: a marker has at most 3 spaces before its `>`,
# since 4 make an indented code block, and takes one space after it, one column of a tab.
QUOTE_MARKERS = re.compile(r"(?: {0,3}> ?)*")
# How far an indented code block's lines are indented (CommonMark §4.4).
CODE_INDENT = 4


def code(body: str) -> list[range]:
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
    """
    column = _column(opening, _top_level(lines, index, opening))
    stop = _fence_stop(lines, index, opening, column)
    return stop.index if stop is not None and stop.closes else index


def _column(opening: re.Match[str], top_level: bool) -> int:
    """Where the text of the fence's list item starts, past its block quotes' markers.

    A top-level fence is in no list item, so a line indented less than its opening one stays in it.
    """
    return 0 if top_level else len(QUOTES.sub("", opening["within"], count=1))


def open_fence(body: str) -> re.Match[str] | None:
    """The opening line of the top-level fence the body ends inside, or None.

    Only a top-level fence runs to the end of the PR body: one in a block quote or a list item ends
    with it at the blank line before the findings. No line leaves a top-level fence.
    """
    lines = list(re.finditer(r".*\n?", body))
    index = 0
    while index < len(lines):
        opening = FENCE.match(lines[index][0])
        if opening is None:
            index += 1
            continue
        top_level = _top_level(lines, index, opening)
        stop = _fence_stop(lines, index, opening, _column(opening, top_level))
        if stop is None:
            return opening if top_level else None
        # The line that leaves a fence's block quote or list item may open a fence of its own.
        index = stop.index + 1 if stop.closes else stop.index
    return None


def _top_level(lines: Sequence[re.Match[str]], index: int, opening: re.Match[str]) -> bool:
    """Whether the fence opened on this line is in no block quote or list item.

    An opening line without their markers is in a list item when it's indented as far as the text
    of an item above, and no line between is indented less, but for the lazy lines that continue a
    paragraph: a line indented less ends the item after a blank line, or when it starts a block.
    """
    return TOP_LEVEL.fullmatch(opening["within"]) is not None and not _in_item(
        lines, index, len(opening["within"])
    )


def _in_item(lines: Sequence[re.Match[str]], index: int, indent: int) -> bool:
    """Whether a line indented this far, with no markers of its own, is in an item above it."""
    for earlier in range(index - 1, -1, -1):
        item = _starts_item(lines, earlier)
        if item is not None and _holds(lines, earlier, item, indent):
            return True
        if _ends_items(lines, earlier, item, indent):
            return False
    return False


def _holds(lines: Sequence[re.Match[str]], index: int, item: re.Match[str], indent: int) -> bool:
    """Whether the item this line starts holds the lines after it indented this far.

    An item that starts with a blank line ends at the next blank line (CommonMark §5.2).
    """
    empty = not lines[index][0][item.end() :].strip()
    return len(item[0]) <= indent and not (empty and not lines[index + 1][0].strip())


def _ends_items(
    lines: Sequence[re.Match[str]], index: int, item: re.Match[str] | None, indent: int
) -> bool:
    """Whether this line ends every list item that would hold a line indented this far.

    A line indented less does, unless it's a lazy one that continues an item's paragraph.
    """
    text = lines[index][0]
    if not text.strip() or _indent(text) >= indent:
        return False
    lazy = _paragraph(text) or (item is None and ITEM.match(text))
    return not lazy or index == 0 or not lines[index - 1][0].strip()


def _starts_item(lines: Sequence[re.Match[str]], index: int) -> re.Match[str] | None:
    """The marker of the list item this line starts, or None if it starts none.

    An empty item, or one numbered other than 1, doesn't interrupt a paragraph (CommonMark §5.2).
    """
    text = lines[index][0]
    item = ITEM.match(text)
    if item is None:
        return None
    empty = not text[item.end() :].strip()
    if (empty or ORDERED_NOT_ONE.match(text)) and index > 0 and _paragraph(lines[index - 1][0]):
        return None
    return item


def _paragraph(line: str) -> bool:
    """Whether this line may be a top-level paragraph's, which a line starting no block continues.

    A paragraph in a block quote doesn't keep an item from starting after it.
    """
    blocks = (ITEM, ALONE, FENCE, QUOTE)
    return bool(line.strip()) and not any(block.match(line) for block in blocks)


@dataclass(frozen=True)
class FenceStop:
    """Where a fence stops: the line that closes it, or the one that leaves its container."""

    index: int
    closes: bool


def _fence_stop(
    lines: Sequence[re.Match[str]], index: int, opening: re.Match[str], column: int
) -> FenceStop | None:
    """Where the fence opened on this line stops, or None if it runs to the end.

    A fence in a block quote or a list item, whose text starts at `column`, ends with it.
    """
    fence, within = opening["fence"], opening["within"]
    in_quotes = re.compile(rf"(?:[ \t]*>[ ]?){{{within.count('>')}}}")
    closing = re.compile(rf" {{0,3}}{fence}{fence[0]}*\s*")
    for later in range(index + 1, len(lines)):
        text = _within(lines[later][0], in_quotes, column)
        if text is None:
            return FenceStop(later, closes=False)
        if closing.fullmatch(text):
            return FenceStop(later, closes=True)
    return None


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


def indented_code(body: str) -> list[range]:
    """Where the body is an indented code block (CommonMark §4.4) out of list items.

    One starts on an indented line that starts the body, or follows a blank line, a line of its own,
    a fenced or an indented code block, or a line in fewer block quotes, and isn't in a list item.
    It goes on over the lines indented as far in those block quotes, and the blank ones. One in a
    list item counts as text.
    """
    lines = list(re.finditer(r".*\n?", body))
    after_fenced = {block.stop for fenced, block in _blocks(body) if fenced}
    found: list[range] = []
    # The block quotes the indented code block going on is in, or None out of one.
    quotes: int | None = None
    for index, line in enumerate(lines):
        depth, text = _quoted(line[0])
        if not text.strip():
            continue
        opens = quotes == depth or _opens_indented(lines, index, after_fenced, quotes)
        quotes = depth if _indent(text) >= CODE_INDENT and opens else None
        if quotes is not None:
            found.append(range(line.start(), line.end()))
    return found


def _opens_indented(
    lines: Sequence[re.Match[str]], index: int, after_fenced: set[int], quotes: int | None
) -> bool:
    """Whether this indented line opens an indented code block: one can't interrupt a paragraph,
    whose lazy line it would be, and in a list item it may be the item's own paragraph.

    `quotes` is the block quotes of the indented code block the lines before end with, or None.
    Only a paragraph has lazy lines, so a line right after a fenced or an indented code block
    interrupts none. Nor does a line in more block quotes than the line before: they open on it.
    """
    if index and quotes is None and lines[index - 1].end() not in after_fenced:
        depth_before, before = _quoted(lines[index - 1][0])
        depth, _ = _quoted(lines[index][0])
        if before.strip() and not ALONE.match(before) and depth_before >= depth:
            return False
    return not _in_item(lines, index, _indent(lines[index][0]))


def _quoted(line: str) -> tuple[int, str]:
    """How many block quotes the line is in, and its text in them, its tabs expanded."""
    expanded = line.expandtabs(4)
    text = QUOTE_MARKERS.sub("", expanded, count=1)
    return expanded[: len(expanded) - len(text)].count(">"), text


def _indent(text: str) -> int:
    """How far the text is indented, a tab reaching the next multiple of 4 (CommonMark §2.2)."""
    expanded = text.expandtabs(4)
    return len(expanded) - len(expanded.lstrip(" "))
