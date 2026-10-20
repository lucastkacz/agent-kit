"""Where an indented code block starts and ends, as `pr_body` reads its own `Closes #N` (#236)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming


@pytest.mark.parametrize(
    "body",
    [
        "# Notes\n    Closes #7\n",
        "Runs:\n\n    make\n    Closes #7\n",
        "Runs:\n\n\tCloses #7\n",
        "- Adds it.\n\nDone.\n\n    Closes #7\n",
    ],
)
def test_an_indented_code_blocks_closes_gets_one_out_of_code(body: str) -> None:
    assert naming.pr_body(body, 7) == f"{body.rstrip()}\n\nCloses #7\n"


@pytest.mark.parametrize("body", ["Adds it.\n    Closes #7\n", "    make\nCloses #7\n"])
def test_a_closes_in_a_paragraph_counts_as_text(body: str) -> None:
    assert naming.pr_body(body, 7) == body


@pytest.mark.parametrize("body", ["    Closes #7", "Runs:\n\n    Closes #7\n"])
def test_building_a_body_with_an_indented_closes_again_changes_nothing(body: str) -> None:
    once = naming.pr_body(body, 7)

    assert naming.pr_body(once, 7) == once
