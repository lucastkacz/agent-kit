"""The reviewer searches the code with the Grep tool and reads it with Read (#174).

In batch #153, three reviews searched with `git grep` through Bash, and each was denied. Allowing
`git grep` isn't safe, since `git grep -O<command>` runs a command, so the skill names the tools.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "review" / "SKILL.md"


def search_line() -> str:
    """The review skill's line that says how to search the code, in lowercase."""
    lines = SKILL.read_text(encoding="utf-8").lower().splitlines()
    found = [line for line in lines if "grep tool" in line]
    assert found, "the review skill names no Grep tool"
    return re.sub(r"\s+", " ", found[0])


def test_the_review_skill_searches_the_code_with_the_grep_tool_and_reads_it_with_read() -> None:
    line = search_line()
    for token in ("search the code with the grep tool", "read it with read"):
        assert token in line, (token, line)


def test_the_review_skill_never_searches_with_grep_rg_or_git_grep_through_bash() -> None:
    line = search_line()
    for token in ("never", "`grep`", "`rg`", "`git grep`", "through bash"):
        assert token in line, (token, line)
