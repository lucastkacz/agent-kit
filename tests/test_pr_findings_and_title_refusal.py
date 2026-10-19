"""A PR body's review findings, and why a title isn't used (small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming
from agent_batch.core.model import Finding

QUOTES_A_CLOSING = Finding("low", "new", "a.py:1", "The comment says it fixes #7.", "Reword it.")
CLOSES_OTHERS = Finding(
    "low",
    "new",
    "a.py:1",
    "This also fixes #12, out of scope.",
    "Fixes: #13; closes owner/repo#14.",
)


def test_the_findings_come_after_the_body_and_before_closes() -> None:
    body = naming.pr_body("Adds it.", 7, (QUOTES_A_CLOSING,))

    assert body.index("Adds it.") < body.index(naming.FINDINGS_HEADING) < body.index("Closes #7")
    assert "- **low** `a.py:1`: The comment says it fixes `#7`." in body


def test_a_findings_closing_references_are_quoted_so_the_merge_closes_nothing_else() -> None:
    body = naming.pr_body("Adds it.", 7, (CLOSES_OTHERS,))

    assert "fixes #12" not in body
    assert "This also fixes `#12`, out of scope." in body
    assert "Fixes: `#13`; closes `owner/repo#14`." in body


def test_a_finding_that_quotes_a_closing_keyword_still_gets_closes() -> None:
    assert naming.pr_body("Adds it.", 7, (QUOTES_A_CLOSING,)).endswith("Closes #7\n")


def test_a_body_that_closes_the_issue_keeps_its_findings_without_a_second_closes() -> None:
    body = naming.pr_body("Closes #7.", 7, (QUOTES_A_CLOSING,))

    assert naming.FINDINGS_HEADING in body
    assert body.count("Closes #7") == 1


@pytest.mark.parametrize(
    ("title", "reason"),
    [
        ("feat: one\nfeat: two", "more than one line"),
        ("feat: " + "x" * 70, "76 characters"),
        ("Added the export", "Conventional Commits"),
    ],
)
def test_a_refused_title_says_why(title: str, reason: str) -> None:
    refusal = naming.title_refusal(title)

    assert refusal is not None
    assert reason in refusal


def test_a_conventional_title_is_not_refused() -> None:
    assert naming.title_refusal("  fix(import): keep dates  ") is None


def test_a_findings_closing_url_is_quoted_too() -> None:
    url = "https://github.com/owner/repo/issues/15"
    finding = Finding("low", "new", "a.py:1", f"It resolves {url}.", "Split it.")

    assert f"It resolves `{url}`." in naming.pr_body("Adds it.", 7, (finding,))
