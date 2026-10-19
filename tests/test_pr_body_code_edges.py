"""Where a PR body's code ends when its closing references are quoted (small tests)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import naming

# Pieces of Markdown that make and break code spans, fences, blocks and closing references.
PIECES = ("fixes ", "Closes ", "fix: ", "#7", "#12", "o/r#7", "`", "``", "```", "~~~", "\\", "\n")
BLOCKS = (" ", "x", "\n- ", "\n## ", "\n> ", "\n| ")
MARKDOWN = st.lists(st.sampled_from(PIECES + BLOCKS)).map("".join)


def test_a_backtick_right_after_a_reference_is_kept_apart_so_no_code_span_moves() -> None:
    # Joined, `#12`` would pair with the next ``, and leave `fixes #13` out of code.
    body = naming.pr_body("Fixes #12` ``fixes #13``", 7)

    assert body.startswith("Fixes `#12` ` ``fixes #13``")


def test_an_escaped_backtick_opens_no_code_span() -> None:
    assert naming.pr_body(r"\`fixes #12\`", 7).startswith(r"\`fixes `#12`\`")


@pytest.mark.parametrize(
    ("written", "quoted"),
    [
        ("`a\n\nfixes #12 `", "`a\n\nfixes `#12` `"),
        ("- Runs `make\n- fixes #12 `", "- Runs `make\n- fixes `#12` `"),
        ("## Runs `make\nfixes #12 `", "## Runs `make\nfixes `#12` `"),
        ("| `make |\n| fixes #12 ` |", "| `make |\n| fixes `#12` ` |"),
    ],
)
def test_a_code_span_ends_with_its_block(written: str, quoted: str) -> None:
    assert naming.pr_body(written, 7).startswith(quoted)


def test_a_code_span_crosses_the_lines_of_its_paragraph() -> None:
    assert naming.pr_body("It keeps `fixes\n#12` as it is.", 7).startswith(
        "It keeps `fixes\n#12` as it is."
    )


def test_a_fence_left_open_runs_to_the_end() -> None:
    body = naming.pr_body("This fixes #13.\n```\nfixes #12", 7)

    assert body.startswith("This fixes `#13`.\n```\nfixes #12")


@given(MARKDOWN)
def test_quoting_a_markdown_body_again_changes_nothing(body: str) -> None:
    once = naming.pr_body(body, 7)

    assert naming.pr_body(once, 7) == once
