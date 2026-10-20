"""A PR body with the review's findings starts as one without: blank lines go, indentation stays.

The findings path has its own strip, and runs in every batch whose approved review has nits (#214).
"""

from __future__ import annotations

import pytest

from agent_batch.core import naming
from agent_batch.core.model import Finding

FINDING = Finding("low", "new", "a.py:1", "It's slow.", "Cache it.")


def test_a_first_line_of_indented_code_keeps_its_indentation_before_the_findings() -> None:
    built = naming.pr_body("    ```\nCloses #7", 7, (FINDING,))

    assert built.startswith("    ```\nCloses #7\n\n## Review findings")


def test_a_body_with_findings_built_again_from_its_own_result_changes_nothing() -> None:
    once = naming.pr_body("    ```\nCloses #7", 7, (FINDING,))

    assert naming.pr_body(once, 7) == once


@pytest.mark.parametrize(
    ("body", "start"),
    [
        ("\n\nCloses #7.", "Closes #7."),
        ("", "## Review findings"),
        ("\r\nCloses #7.", "Closes #7."),
    ],
)
def test_a_body_with_findings_starts_with_its_first_line_of_text(body: str, start: str) -> None:
    assert naming.pr_body(body, 7, (FINDING,)).startswith(start)


def test_a_body_that_starts_with_a_windows_blank_line_starts_with_its_first_line_of_text() -> None:
    assert naming.pr_body("\r\nAdds a thing.", 7) == "Adds a thing.\n\nCloses #7\n"
