"""An indented `Closes #N` after a fenced block or in a block quote is code, and a tab-indented
line's indent counts its tabs to the next multiple of 4, as GitHub reads them (#251)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import naming


@pytest.mark.parametrize(
    "body",
    [
        "```\ncode\n```\n    Closes #7",
        "~~~\ncode\n~~~\n    Closes #7\n",
        "Runs:\n\n```\nmake\n```\n\tCloses #7\n",
        "> ```\n> code\n> ```\n>     Closes #7\n",
    ],
)
def test_an_indented_closes_right_after_a_fenced_block_is_code(body: str) -> None:
    assert naming.pr_body(body, 7) == f"{body.rstrip()}\n\nCloses #7\n"


@pytest.mark.parametrize(
    "body",
    [
        ">\n>     Closes #7",
        "> Runs:\n>\n>     make\n>     Closes #7\n",
        "> Runs:\n>\n>\t\tCloses #7\n",
        "> # Notes\n>     Closes #7\n",
    ],
)
def test_an_indented_closes_in_a_block_quote_is_code(body: str) -> None:
    assert naming.pr_body(body, 7) == f"{body.rstrip()}\n\nCloses #7\n"


@pytest.mark.parametrize("body", ["> Adds it.\n>     Closes #7\n", "> Adds it.\n    Closes #7\n"])
def test_an_indented_closes_in_a_block_quotes_paragraph_is_text(body: str) -> None:
    assert naming.pr_body(body, 7) == body


@pytest.mark.parametrize("indent", ["\t", " \t", "  \t", "   \t", "  \t  "])
def test_a_tab_indented_list_continuation_is_text(indent: str) -> None:
    body = f"- Adds it.\n\n{indent}Closes #7"

    assert naming.pr_body(body, 7) == body


@given(
    indent=st.text(alphabet=" \t", min_size=1, max_size=6),
    before=st.sampled_from(["- Adds it.\n\n", "Runs:\n\n", "```\nmake\n```\n", ">\n", ""]),
)
def test_a_tab_reads_as_the_spaces_to_the_next_multiple_of_4(indent: str, before: str) -> None:
    tabbed = f"{before}{indent}Closes #7"
    spaced = f"{before}{indent.expandtabs(4)}Closes #7"

    assert naming.pr_body(tabbed, 7).endswith("\n\nCloses #7\n") == naming.pr_body(
        spaced, 7
    ).endswith("\n\nCloses #7\n")
