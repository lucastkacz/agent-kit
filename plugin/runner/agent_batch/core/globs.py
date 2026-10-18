"""Path patterns for risk paths.

A pattern with a `/` is matched from the repository's root; one without is matched against the
file name at any depth. `**` crosses folders, `*` and `?` don't, and a trailing `/` means
everything inside a folder.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import cache


@cache
def compile_pattern(pattern: str) -> re.Pattern[str]:
    text = pattern.strip()
    if text.endswith("/"):
        text += "**"
    anchored = "/" in text
    body = _translate(text.lstrip("/"))
    return re.compile(f"^{body}$" if anchored else f"^(?:.*/)?{body}$")


def _translate(text: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(text):
        if text.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif text.startswith("**", index):
            parts.append(".*")
            index += 2
        else:
            parts.append(_single(text[index]))
            index += 1
    return "".join(parts)


def _single(char: str) -> str:
    if char == "*":
        return "[^/]*"
    if char == "?":
        return "[^/]"
    return re.escape(char)


def first_match(path: str, patterns: Sequence[str]) -> str | None:
    """The first pattern that matches the path, if any."""
    return next((p for p in patterns if compile_pattern(p).match(path)), None)
