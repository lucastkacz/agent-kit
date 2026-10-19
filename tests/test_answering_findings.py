"""The implementer knows it can answer a review finding instead of fixing it, and how (#103)."""

from __future__ import annotations

from pathlib import Path

from agent_batch.core import prompts
from agent_batch.core.model import Finding

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "implement" / "SKILL.md"
FINDING = Finding("medium", "new", "a.py:1", "It breaks.", "Fix it.")


def fix_prompt() -> str:
    return prompts.fix(7, [FINDING])


def section(heading: str) -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index(f"\n## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def test_the_fix_prompt_says_each_finding_is_fixed_or_answered_and_how_to_answer() -> None:
    prompt = fix_prompt()

    assert prompt.startswith("The reviewer asked for changes on #7"), prompt
    assert "fix or answer each finding" in prompt.lower(), prompt
    assert "a commit whose subject names the finding's location" in prompt, prompt
    assert "whose body says why it stays as it is" in prompt, prompt
    assert "a code comment where the finding points" in prompt, prompt


def test_the_fix_prompt_always_fixes_findings_about_checks_tests_and_criteria() -> None:
    prompt = fix_prompt()

    assert "Always fix a finding about" in prompt, prompt
    rule = prompt[prompt.index("Always fix a finding about") :].split("\n")[0]
    assert "`make check`" in rule, rule
    assert "acceptance tests" in rule, rule
    assert "unmet criterion" in rule, rule


def test_the_implement_skill_gives_the_rule_in_the_same_session_and_in_direct_mode() -> None:
    answer, direct = section("6. Answer"), section("Direct mode")

    for text in (answer, direct):
        assert "fix or answer each finding" in text.lower(), text
    assert "a commit whose subject names the finding's location" in answer, answer
    assert "whose body says why it stays as it is" in answer, answer
    assert "a code comment where the finding points" in answer, answer
    assert "Always fix a finding about `make check`" in answer, answer
    assert "unmet criterion" in answer, answer
    assert "the rule in step 6" in direct, direct
