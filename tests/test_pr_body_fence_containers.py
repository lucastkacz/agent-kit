"""Whether a fence left open is top-level, or ends with its list item (#138, small tests)."""

from __future__ import annotations

import pytest

from agent_batch.core import naming


@pytest.mark.parametrize(
    "written",
    [
        "- Runs:\nlazily\n  ```\n  make",
        "1. Runs:\n\n   ```\n   make",
        "- Runs:\n  - make:\n\n  ```\n  make",
    ],
)
def test_a_fence_indented_into_a_list_item_gets_no_closing(written: str) -> None:
    assert naming.pr_body(written, 7) == f"{written}\n\nCloses #7\n"


@pytest.mark.parametrize(
    ("written", "closing"),
    [
        ("- \n\n  ```\nmake", "  ```"),
        ("Runs:\n- \n  ```\nmake", "  ```"),
        ("- Runs:\n> make:\n  ```\nmake", "  ```"),
        ("Runs:\n2. make\n   ~~~\nmake", "   ~~~"),
        ("- Runs:\n\nmake:\n  ```\nmake", "  ```"),
    ],
)
def test_a_fence_out_of_every_list_item_is_closed(written: str, closing: str) -> None:
    assert naming.pr_body(written, 7) == f"{written}\n{closing}\n\nCloses #7\n"
