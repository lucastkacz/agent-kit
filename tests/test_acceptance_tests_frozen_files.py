"""Which acceptance-test files stay frozen, and what a wrong one's question recommends (#237).

SPEC §5, the implement skill and the review skill must say the same, so these check the facts.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from skill_files import PLUGIN
from spec_text import SPEC, flat

FROZEN = (
    "the test files it adds or changes",
    "shared test code it touches, such as `conftest.py` or a helper module, may change later",
)


def spec_step_2() -> str:
    return flat(SPEC.read_text(encoding="utf-8"), "2. **Acceptance tests first.**", "\n3. **")


def skill(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def implement_acceptance_step() -> str:
    return flat(skill("implement"), "## 2. Acceptance tests first", "\n## 3. ")


def review_acceptance_check() -> str:
    return flat(skill("review"), "3. **Acceptance tests unchanged.**", "\n4. **")


@pytest.mark.parametrize("token", FROZEN)
def test_spec_5_freezes_only_the_test_files_the_acceptance_commit_adds_or_changes(
    token: str,
) -> None:
    step = spec_step_2()
    assert token in step, (token, step)


@pytest.mark.parametrize("token", FROZEN)
@pytest.mark.parametrize("text", [implement_acceptance_step, review_acceptance_check])
def test_the_implement_and_review_skills_freeze_the_same_files_in_the_spec_s_terms(
    text: Callable[[], str], token: str
) -> None:
    step = text()
    assert token in step, (token, step)


def test_a_wrong_acceptance_tests_question_recommends_fixing_it_in_the_acceptance_commit() -> None:
    step = implement_acceptance_step()
    for token in (
        "recommends fixing the test inside the acceptance commit",
        "rebuilding the branch on `master`",
        "once the owner approves (spec §5)",
    ):
        assert token in step, (token, step)


def test_a_wrong_acceptance_tests_question_never_offers_a_later_commit_on_its_file() -> None:
    step = implement_acceptance_step()
    assert "don't offer a later commit that changes an acceptance test's file" in step, step
    assert "the review blocks it" in step, step
