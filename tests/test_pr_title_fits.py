"""The PR title built from the issue fits in MAX_TITLE characters (small tests)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import naming
from agent_batch.core.model import Issue

REFUSED = "Added the export"


def issue(title: str, labels: frozenset[str] = frozenset()) -> Issue:
    return Issue(66, title, "", "owner", labels, "OPEN")


def test_a_long_issue_title_is_cut_at_a_word_boundary() -> None:
    long_title = "Re-running a batch skips a merged issue and then defers the rest of its lane"

    title = naming.pr_title(REFUSED, issue(long_title, frozenset({"bug"})))

    assert title == "fix: Re-running a batch skips a merged issue and then defers the rest of"
    assert len(title) == naming.MAX_TITLE


def test_an_issue_title_that_fits_is_kept_whole() -> None:
    fitting = "x" * (naming.MAX_TITLE - len("feat: "))

    assert naming.pr_title(REFUSED, issue(fitting)) == f"feat: {fitting}"


def test_a_first_word_too_long_to_fit_is_cut() -> None:
    title = naming.pr_title(REFUSED, issue("a" * 100 + " export"))

    assert title == "feat: " + "a" * (naming.MAX_TITLE - len("feat: "))


@given(
    st.one_of(st.text(), st.text(min_size=naming.MAX_TITLE)),
    st.sampled_from([frozenset(), frozenset({"bug"}), frozenset({"spike"})]),
)
def test_a_title_built_from_any_issue_title_fits(title: str, labels: frozenset[str]) -> None:
    built = naming.pr_title(REFUSED, issue(title, labels))

    assert len(built) <= naming.MAX_TITLE
