"""A PR body's `Closes #N` and findings stay out of code, and every reference GitHub reads once the
Markdown is rendered is quoted (#138, small tests)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import naming
from agent_batch.core.model import Finding

FINDING = Finding("low", "new", "a.py:1", "It's slow.", "Cache it.")
LISTED = "## Review findings\n\n- **low** `a.py:1`: It's slow. Suggestion: Cache it.\n\nCloses #7\n"


@pytest.mark.parametrize(
    ("written", "closed"),
    [
        ("Runs:\n```bash\nmake check\n", "Runs:\n```bash\nmake check\n```"),
        ("Runs:\n\n~~~~\nmake check", "Runs:\n\n~~~~\nmake check\n~~~~"),
        ("Runs:\n  ````\nmake ``check``\n\n", "Runs:\n  ````\nmake ``check``\n  ````"),
        ("Runs:\n```", "Runs:\n```\n```"),
        ("- ```\n  make\n```\nmake check", "- ```\n  make\n```\nmake check\n```"),
        ("> ```\n> make\n```\nmake check", "> ```\n> make\n```\nmake check\n```"),
    ],
)
def test_a_body_ending_inside_an_unclosed_top_level_fence_is_closed_before_the_additions(
    written: str, closed: str
) -> None:
    assert naming.pr_body(written, 7, (FINDING,)) == f"{closed}\n\n{LISTED}"


def test_a_closes_inside_an_unclosed_fence_is_code_so_the_body_still_gets_one() -> None:
    assert (
        naming.pr_body("Runs:\n```\nCloses #7\n", 7) == "Runs:\n```\nCloses #7\n```\n\nCloses #7\n"
    )


@pytest.mark.parametrize(
    "written",
    ["- ```\n  make check\n", "> ```\n> make check\n", "1. Runs:\n   ```\n   make check"],
)
def test_an_unclosed_fence_in_a_list_item_or_a_block_quote_ends_with_it_and_gets_no_closing(
    written: str,
) -> None:
    assert naming.pr_body(written, 7, (FINDING,)) == f"{written.rstrip()}\n\n{LISTED}"


@pytest.mark.parametrize(
    ("written", "quoted"),
    [
        ("It also fixes \\#12.", "It also fixes `#12`."),
        ("It also closes owner/repo\\#14.", "It also closes `owner/repo#14`."),
        ("Fixes: \\#13.", "Fixes: `#13`."),
        ("> It also fixes\n> #12.", "> It also fixes\n> `#12`."),
        ("> It also\n> > resolves\n> > o/r#14.", "> It also\n> > resolves\n> > `o/r#14`."),
    ],
)
def test_a_reference_github_reads_once_rendered_is_quoted_in_the_body(
    written: str, quoted: str
) -> None:
    assert naming.pr_body(written, 7) == f"{quoted}\n\nCloses #7\n"


@pytest.mark.parametrize("written", ["Closes \\#7.", "> This closes\n> #7."])
def test_a_body_closing_the_issue_once_rendered_gets_no_second_closes(written: str) -> None:
    assert naming.pr_body(written, 7) == written


def test_a_reference_github_reads_once_rendered_is_quoted_in_the_findings() -> None:
    finding = Finding("low", "new", "a.py:1", "It fixes \\#12.", "Say it fixes\n> #13.")

    body = naming.pr_body("Adds it.", 7, (finding,))

    assert "It fixes `#12`. Suggestion: Say it fixes\n> `#13`." in body


# Pieces of a body none of whose fences is left open and whose references read as written, each with
# how it comes out: a closing reference to another issue is quoted, and one in code stays as it is.
TEXT = st.sampled_from(
    [
        ("Adds it.", "Adds it."),
        ("fixes #12", "fixes `#12`"),
        ("Closes: owner/repo#14", "Closes: `owner/repo#14`"),
        ("resolves #7", "resolves #7"),
        ("closes o/r#7", "closes `o/r#7`"),
        ("`fixes #12`", "`fixes #12`"),
        ("``a ` fixes #12``", "``a ` fixes #12``"),
        ("\n```bash\nfixes #12\n```\n", "\n```bash\nfixes #12\n```\n"),
        ("\n~~~\nCloses #7\n~~~\n", "\n~~~\nCloses #7\n~~~\n"),
        ("\n- ```\n  fixes #12\n  ```\n", "\n- ```\n  fixes #12\n  ```\n"),
    ]
)
SEPARATORS = st.sampled_from([" ", "\n", "\n\n", "\n- ", "\n## ", "\n1. "])
CLOSES_ITS_ISSUE = ("resolves #7",)


@given(st.lists(st.tuples(TEXT, SEPARATORS), min_size=1))
def test_a_body_without_such_cases_comes_out_as_before(
    pieces: list[tuple[tuple[str, str], str]],
) -> None:
    written = "".join(text + separator for (text, _), separator in pieces)
    quoted = "".join(out + separator for (_, out), separator in pieces)
    closes = any(text in CLOSES_ITS_ISSUE for (text, _), _ in pieces)

    expected = quoted if closes else f"{quoted.rstrip()}\n\nCloses #7\n".lstrip()
    assert naming.pr_body(written, 7) == expected
