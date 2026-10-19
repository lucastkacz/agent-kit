"""Where a PR body's code is, for the closing references the merge reads (small tests)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import naming

# Pieces of Markdown that make and break code spans, fences, blocks and closing references.
PIECES = ("fixes ", "Closes ", "fix: ", "#7", "#12", "o/r#7", "`", "``", "```", "~~~", "\\", "\n")
BLOCKS = (" ", "x", "\n- ", "\n1. ", "\n## ", "\n> ", "\n| ", "\n---", "\n   ")
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


def test_a_fence_that_never_closes_is_read_as_text() -> None:
    # A misread fence would leave the rest of the body out of the quoting.
    body = naming.pr_body("This fixes #13.\n```\nfixes #12", 7)

    assert body.startswith("This fixes `#13`.\n```\nfixes `#12`")


@pytest.mark.parametrize(
    "fenced",
    [
        "1. ```bash\n   fixes #11\n   ```\n",
        "- ```\n  fixes #11\n  ```\n",
        "> ```\n> fixes #11\n> ```\n",
        "```markdown\n> ```\nfixes #11\n```\n",
    ],
)
def test_a_fence_in_a_list_item_or_a_block_quote_closes_where_it_does(fenced: str) -> None:
    body = naming.pr_body(f"{fenced}2. This also fixes #12.", 7)

    assert body.startswith(f"{fenced}2. This also fixes `#12`.")


@pytest.mark.parametrize(("marker", "inside"), [("> ", "> "), ("- ", "  ")])
def test_a_fence_ends_with_its_block_quote_or_list_item(marker: str, inside: str) -> None:
    # The line out of the quote or the item ends the fence, so the last line doesn't close it.
    body = f"{marker}```\n{inside}make\nThis also fixes #12.\n{inside}```\n"

    assert "This also fixes `#12`." in naming.pr_body(body, 7)


@pytest.mark.parametrize("rule", ["---", "***", "* * *", "___", "===", "-"])
def test_a_code_span_ends_at_a_rule_or_an_underline(rule: str) -> None:
    body = naming.pr_body(f"Adds `make\n{rule}\nThis also fixes #12 and keeps `a`.", 7)

    assert body.startswith(f"Adds `make\n{rule}\nThis also fixes `#12` and keeps `a`.")


def test_a_closes_in_code_doesnt_close_the_issue_so_the_body_gets_one() -> None:
    assert naming.pr_body("Says `Closes #7` in code.", 7).endswith("\n\nCloses #7\n")


def test_a_closes_with_a_colon_gets_no_second_one() -> None:
    assert naming.pr_body("Fixes: #7.", 7) == "Fixes: #7."


@given(MARKDOWN)
def test_quoting_a_markdown_body_again_changes_nothing(body: str) -> None:
    once = naming.pr_body(body, 7)

    assert naming.pr_body(once, 7) == once
