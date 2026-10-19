"""The references in a fence the body leaves open stay as written, since the closed fence makes them
code (#138, small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming


@pytest.mark.parametrize(
    ("written", "closing"),
    [
        ("Runs:\n```\nfixes #12\n", "```"),
        ("Runs:\n  ~~~\nIt closes o/r#14 and fixes \\#12.", "  ~~~"),
    ],
)
def test_a_reference_inside_an_unclosed_fence_gets_no_backticks(written: str, closing: str) -> None:
    assert naming.pr_body(written, 7) == f"{written.rstrip()}\n{closing}\n\nCloses #7\n"


def test_a_reference_before_an_unclosed_fence_is_still_quoted() -> None:
    assert (
        naming.pr_body("It fixes #12.\n\n```\nfixes #12\n", 7)
        == "It fixes `#12`.\n\n```\nfixes #12\n```\n\nCloses #7\n"
    )
