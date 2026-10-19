"""A top-level fence indented 1 to 3 spaces holds the lines indented less (#138, small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming


def test_a_closes_inside_an_unclosed_indented_fence_is_code_so_the_body_still_gets_one() -> None:
    assert (
        naming.pr_body("Runs:\n  ```\nCloses #7\n", 7)
        == "Runs:\n  ```\nCloses #7\n  ```\n\nCloses #7\n"
    )


@pytest.mark.parametrize(
    "written", ["Runs:\n  ```\nCloses #7\n  ```\n", "Runs:\n   ~~~\n Closes #7\n~~~\n"]
)
def test_a_closes_inside_a_closed_indented_fence_is_code_so_the_body_still_gets_one(
    written: str,
) -> None:
    assert naming.pr_body(written, 7) == f"{written}\nCloses #7\n"
