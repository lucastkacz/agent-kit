"""The reviewer asks for a test instead of probing a behavior with code of its own (#109).

At batch #82, three of the reviewers' seven denials were `python -c` probes of a function's output.
`python -c` stays denied, since the reviewer is read-only: a behavior it would have to probe is one
no test shows, and that's the finding.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "review" / "SKILL.md"


def skill_text() -> str:
    """The review skill in lowercase, on one line."""
    return re.sub(r"\s+", " ", SKILL.read_text(encoding="utf-8")).lower()


def test_the_review_skill_makes_a_behavior_no_test_covers_a_missing_test_finding() -> None:
    text = skill_text()
    for token in ("a behavior no test covers is a finding", "a missing test"):
        assert token in text, token


def test_the_review_skill_says_the_reviewer_reads_and_never_runs_code_of_its_own() -> None:
    text = skill_text()
    for token in (
        "never run code of your own to probe it", "`python -c`", "a script",
        "read the code and its tests", "you may run `make test`",
    ):  # fmt: skip
        assert token in text, token
