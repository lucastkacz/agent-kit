"""Branch names, PR titles and bodies, and risk path patterns (small tests)."""

from __future__ import annotations

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import globs, naming
from agent_batch.core.model import Issue


def issue(
    number: int = 7, title: str = "Export cards", labels: frozenset[str] = frozenset()
) -> Issue:
    return Issue(number, title, "", "owner", labels, "OPEN")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Export cards to CSV", "7-export-cards-to-csv"),
        ("Añadir exportación (beta)!", "7-anadir-exportacion-beta"),
        ("¿¿??", "7"),
        ("a" * 60, "7-" + "a" * 40),
    ],
)
def test_branch_names_are_short_ascii_slugs(title: str, expected: str) -> None:
    assert naming.branch_name(issue(title=title)) == expected


@given(st.integers(min_value=1, max_value=10**6), st.text())
def test_a_branch_name_is_always_safe_and_short(number: int, title: str) -> None:
    name = naming.branch_name(issue(number, title))
    assert re.fullmatch(r"\d+(-[a-z0-9]+)*", name)
    assert name.startswith(str(number))
    assert len(name) <= len(str(number)) + 1 + naming.MAX_SLUG


def test_a_conventional_title_is_kept() -> None:
    assert naming.pr_title("fix(import): keep dates", issue()) == "fix(import): keep dates"


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (frozenset(), "feat: Export cards"),
        (frozenset({"bug"}), "fix: Export cards"),
        (frozenset({"spike"}), "docs: Export cards"),
    ],
)
def test_a_title_that_breaks_the_convention_is_rebuilt_from_the_issue(
    labels: frozenset[str], expected: str
) -> None:
    assert naming.pr_title("Added the export", issue(labels=labels)) == expected


def test_a_body_gets_closes_once() -> None:
    assert naming.pr_body("Adds it.", 7) == "Adds it.\n\nCloses #7\n"
    assert naming.pr_body("Fixes #7 for good.", 7) == "Fixes #7 for good."
    assert naming.pr_body("See #70.", 7).endswith("Closes #7\n")


@given(st.text(), st.integers(min_value=1, max_value=10**6))
def test_closing_the_issue_is_idempotent(body: str, number: int) -> None:
    once = naming.pr_body(body, number)
    assert naming.pr_body(once, number) == once
    assert f"#{number}" in once


@pytest.mark.parametrize(
    ("path", "pattern", "matches"),
    [
        (".github/workflows/ci.yml", ".github/", True),
        ("src/.github/x", ".github/", False),
        ("Makefile", "Makefile", True),
        ("tools/Makefile", "Makefile", True),
        ("src/app/migrations/0001.sql", "**/migrations/", True),
        ("migrations/0001.sql", "**/migrations/", True),
        ("requirements-dev.txt", "requirements*.txt", True),
        ("src/requirements/dev.txt", "requirements*.txt", False),
        ("src/core/money.py", "src/core/*.py", True),
        ("src/core/sub/money.py", "src/core/*.py", False),
        ("src/core/sub/money.py", "src/core/**", True),
        ("a.key", "*.key", True),
        ("a.keys", "*.key", False),
    ],
)
def test_patterns(path: str, pattern: str, matches: bool) -> None:
    assert (globs.first_match(path, [pattern]) is not None) is matches


@given(st.from_regex(r"[a-z0-9_.]{1,8}(/[a-z0-9_.]{1,8}){0,3}", fullmatch=True))
def test_a_path_matches_itself_and_double_star_matches_everything(path: str) -> None:
    assert globs.first_match(path, [f"/{path}"]) is not None
    assert globs.first_match(path, ["**"]) is not None


def test_the_first_matching_pattern_is_reported() -> None:
    assert globs.first_match("a/b.py", ["*.md", "*.py", "a/"]) == "*.py"
    assert globs.first_match("a/b.py", ["*.md"]) is None
