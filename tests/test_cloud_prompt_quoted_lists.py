"""The lists the cloud prompt quotes as complete stay complete, and its rules hide no line (#79).

The acceptance tests pin each quoted item on its own, so an item added to a SPEC list would pass
unnoticed. These pin the whole lists, and fail on a line of the prompt's rules that the quote
check would skip.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPEC.md"
PROMPT = ROOT / "plugin" / "skills" / "run-batch" / "cloud-prompt.md"

# SPEC §7.1's reasons for a human check, which the prompt's Verification rule gives as all of them.
HUMAN_REASONS = (
    "Taste:",
    "Physical hardware,",
    "Real accounts, real money or real personal data.",
    "A third-party service without a test environment.",
)
# SPEC §8.2's limits: the prompt's Limits rule quotes the last four, the implement skill the rest.
LIMITS = (
    "Lines per source file",
    "Lines per function",
    "Cognitive complexity per function",
    "Parameters per function",
    "Coverage of new and changed code",
    "Type checking",
    "Warnings",
)
# The lines of the prompt's rules that the quote check reads, or knowingly leaves out.
READ_LINES = ("- **", "<!--", "The process's rules,")


def section(text: str, heading: str) -> str:
    """The text from `heading` to the next heading of the same or a higher level."""
    start = text.index(heading)
    ends = [end for marker in ("\n## ", "\n### ") if (end := text.find(marker, start + 1)) != -1]
    return text[start : min(ends, default=len(text))]


def test_the_human_reasons_the_prompt_gives_are_all_of_spec_7_1s() -> None:
    text = section(SPEC.read_text(encoding="utf-8"), "### 7.1 ")
    reasons = tuple(re.findall(r"^  \d+\. \*\*(.+?)\*\*", text, re.MULTILINE))
    assert reasons == HUMAN_REASONS, (
        f"SPEC §7.1's reasons for a human check are now {reasons}. The cloud prompt's Verification"
        " rule gives them as the only ones: change it to match, and HUMAN_REASONS."
    )


def test_the_limits_the_prompt_and_the_implement_skill_quote_are_all_of_spec_8_2s() -> None:
    text = section(SPEC.read_text(encoding="utf-8"), "### 8.2 ")
    rows = re.findall(r"^\| (.+?) \| .+? \|$", text, re.MULTILINE)
    limits = tuple(row for row in rows if row != "Limit")
    assert limits == LIMITS, (
        f"SPEC §8.2's limits are now {limits}. The cloud prompt's Limits rule and the implement"
        " skill quote them: change them to match, and LIMITS."
    )


def test_every_line_of_the_prompts_rules_is_one_the_quote_check_reads() -> None:
    rules = section(PROMPT.read_text(encoding="utf-8"), "## The rules")
    unread = [
        line for line in rules.splitlines()[1:] if line.strip() and not line.startswith(READ_LINES)
    ]
    assert not unread, (
        f"The cloud prompt's rules have lines the quote check skips: {unread}. Write each rule as"
        " one `- **Label.**` bullet on a single line."
    )
