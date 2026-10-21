"""A tab-indented line keeps a list item going, as one indented with spaces as far does (#251)."""

from __future__ import annotations

from agent_batch.core import naming


def test_a_closes_after_a_tab_indented_paragraph_of_a_list_item_is_text() -> None:
    body = "- Adds it.\n\n\tTests it.\n\n\tCloses #7\n"

    assert naming.pr_body(body, 7) == body
