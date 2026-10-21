"""An indented line that opens a block quote, or follows an indented code block, is code: only a
paragraph has lazy lines (#251's review)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming


@pytest.mark.parametrize(
    "body",
    [
        "Adds it.\n>     Closes #7",
        "Runs:\n>     make\n>     Closes #7\n",
        ">     make\n    Closes #7",
        "    make\n>     Closes #7",
    ],
)
def test_an_indented_closes_in_a_new_block_quote_or_after_code_is_code(body: str) -> None:
    assert naming.pr_body(body, 7) == f"{body.rstrip()}\n\nCloses #7\n"


@pytest.mark.parametrize("body", ["> Adds it.\n    Closes #7\n", "> > Adds it.\n>     Closes #7\n"])
def test_an_indented_closes_after_a_deeper_quotes_paragraph_is_its_lazy_line(body: str) -> None:
    assert naming.pr_body(body, 7) == body
