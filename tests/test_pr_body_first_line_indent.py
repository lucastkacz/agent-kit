"""A PR body's first line keeps its indentation, so building the body again changes nothing (#214).

Four spaces make a line code; without them, a line of three backticks opens a fence.
"""

from __future__ import annotations

import pytest

from agent_batch.core import naming

INDENTED_FIRST_LINES = ("\n    ```", "    ```", "\n\n    x = 1\n", " \n    ~~~\nfixes #12")


@pytest.mark.parametrize("body", INDENTED_FIRST_LINES)
def test_a_first_line_of_indented_code_keeps_its_indentation(body: str) -> None:
    first = body.lstrip(" \n").split("\n")[0]

    assert naming.pr_body(body, 7).startswith(f"    {first}")


@pytest.mark.parametrize("body", [*INDENTED_FIRST_LINES, "   ```\nfixes #12", "\n  - a\n    ```"])
def test_building_a_body_again_from_its_own_result_changes_nothing(body: str) -> None:
    once = naming.pr_body(body, 7)

    assert naming.pr_body(once, 7) == once


@pytest.mark.parametrize(
    ("body", "built"),
    [
        ("", "Closes #7\n"),
        ("\n\nAdds a thing.", "Adds a thing.\n\nCloses #7\n"),
        (" \n\t\nAdds a thing.", "Adds a thing.\n\nCloses #7\n"),
    ],
)
def test_a_body_that_starts_with_blank_lines_starts_with_its_first_line_of_text(
    body: str, built: str
) -> None:
    assert naming.pr_body(body, 7) == built
