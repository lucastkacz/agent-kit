"""The implementer's PR body closes its own issue and no other (#95, small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming

URL = "https://github.com/owner/repo/issues/15"


@pytest.mark.parametrize(
    ("written", "quoted"),
    [
        ("this also fixes #12", "this also fixes `#12`"),
        ("Fixes: #13", "Fixes: `#13`"),
        ("closes owner/repo#14", "closes `owner/repo#14`"),
        (f"resolves {URL}", f"resolves `{URL}`"),
    ],
)
def test_the_bodys_closing_references_to_other_issues_come_out_in_code(
    written: str, quoted: str
) -> None:
    body = naming.pr_body(f"Adds it, and {written}.", 7)

    assert body == f"Adds it, and {quoted}.\n\nCloses #7\n"


def test_a_body_that_closes_the_issue_keeps_it_as_written_and_gets_no_second_closes() -> None:
    body = naming.pr_body("Closes #7.\n\nThis also fixes #12.\n", 7)

    assert body == "Closes #7.\n\nThis also fixes `#12`.\n"


def test_the_issue_named_in_another_form_is_quoted_and_the_body_gets_closes() -> None:
    body = naming.pr_body("It closes owner/repo#7.", 7)

    assert body == "It closes `owner/repo#7`.\n\nCloses #7\n"


@pytest.mark.parametrize(
    ("written", "quoted"),
    [
        ("`fixes #12` stays, this fixes #13.", "`fixes #12` stays, this fixes `#13`."),
        ("``fixes #12`` stays, this fixes #13.", "``fixes #12`` stays, this fixes `#13`."),
        ("```\nfixes #12\n```\nThis fixes #13.", "```\nfixes #12\n```\nThis fixes `#13`."),
        ("~~~text\nfixes #12\n~~~\nThis fixes #13.", "~~~text\nfixes #12\n~~~\nThis fixes `#13`."),
    ],
)
def test_a_closing_reference_already_in_code_is_left_as_written(written: str, quoted: str) -> None:
    assert naming.pr_body(written, 7) == f"{quoted}\n\nCloses #7\n"
