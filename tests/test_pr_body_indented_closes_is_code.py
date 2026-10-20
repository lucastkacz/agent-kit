"""A `Closes #N` in an indented code block is code, so the PR body still gets one outside code,
but one in a list item's indented continuation is text (#236, small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming
from agent_batch.core.model import Finding

FINDING = Finding("low", "new", "a.py:1", "It's slow.", "Cache it.")


@pytest.mark.parametrize(
    "body", ["    Closes #7", "Adds it.\n\n    Closes #7\n", "Runs:\n\n    make\n\n    Closes #7"]
)
def test_an_indented_closes_is_code_so_the_body_still_ends_with_closes(body: str) -> None:
    built = naming.pr_body(body, 7)

    assert built.startswith(body.rstrip())
    assert built.endswith("\n\nCloses #7\n")


def test_an_indented_closes_with_findings_still_ends_with_closes_after_them() -> None:
    built = naming.pr_body("    Closes #7", 7, (FINDING,))

    assert built.startswith("    Closes #7\n\n## Review findings")
    assert built.endswith(f"{FINDING.suggestion}\n\nCloses #7\n")


@pytest.mark.parametrize(
    "body",
    [
        "- Adds it.\n\n    Closes #7\n",
        "1. Adds it.\n\n    Closes #7\n",
        "- Adds it.\n    Closes #7\n",
    ],
)
def test_a_closes_in_a_list_items_indented_continuation_still_counts_as_text(body: str) -> None:
    assert naming.pr_body(body, 7) == body
    assert naming.pr_body(body, 7, (FINDING,)).count("Closes #7") == 1
