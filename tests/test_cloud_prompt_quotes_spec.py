"""The rules the cloud prompt quotes stay in step with their sources in SPEC §5, §7 and §8 (#79).

A project's repository has neither the SPEC nor the kit, so the cloud prompt quotes the rules
in its own words. Each sentence of its rules is paired here with the SPEC text it comes from:
when one side changes without the other, a test fails and names both.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPEC.md"
PROMPT = ROOT / "plugin" / "skills" / "run-batch" / "cloud-prompt.md"

# (a sentence of the prompt's rules, the SPEC section it quotes, the SPEC text it comes from).
QUOTES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "A `unit`, `integration` or `e2e` criterion gets a test in the repository.",
        "7.1",
        ("- `unit`, `integration` or `e2e`: a test in the repository.",),
    ),
    (
        "`human(<reason>)` is only for taste, physical hardware or an operating-system permission"
        " dialog, real accounts, money or personal data, or a third-party service without a test"
        " environment.",
        "7.1",
        (
            "`human(<reason>)`, only for one of these reasons:",
            "**Taste:** whether it looks or feels right.",
            "**Physical hardware,** or an operating-system permission dialog.",
            "**Real accounts, real money or real personal data.**",
            "**A third-party service without a test environment.**",
        ),
    ),
    (
        "The review blocks a criterion without its test, a `human` item that could be automated,"
        " and acceptance tests changed after their commit.",
        "7.1",
        (
            "The reviewer blocks when a criterion has no test, when a `human` item could be"
            " automated, or when the acceptance tests changed after their commit.",
        ),
    ),
    (
        "`make test` runs the small and medium tests and stays under 30 seconds; `make e2e` runs"
        " the ones that drive the app, for UI criteria, and keeps their evidence.",
        "7.3",
        (
            "Large tests drive the running app.",
            "`make test` runs the small and medium ones; `make e2e` runs the large ones.",
            "`make test` finishes in under 30 seconds",
        ),
    ),
    (
        "`make test` runs the small and medium tests and stays under 30 seconds; `make e2e` runs"
        " the ones that drive the app, for UI criteria, and keeps their evidence.",
        "5",
        ("**Visible behavior.** `make e2e` for UI criteria, keeping its evidence.",),
    ),
    (
        "Fixtures are made by hand, never copied from real data.",
        "7.4",
        ("- Fixtures are made by hand, never copied from real data.",),
    ),
    (
        "Logic with many possible inputs, such as parsing, calculations or state machines, also"
        " gets property-based tests.",
        "7.7",
        (
            "Logic with many possible inputs, such as parsing, calculations or state machines,"
            " gets property-based tests on top of examples",
        ),
    ),
    (
        "At most 5 parameters per function, 80% coverage of new and changed code, strict type"
        " checking, and warnings treated as errors, on top of the implement skill's limits.",
        "8.2",
        (
            "| Parameters per function | 5 |",
            "| Coverage of new and changed code | 80% |",
            "| Type checking | Strict |",
            "| Warnings | Treated as errors |",
        ),
    ),
    (
        "Generated code and test fixtures are exempt.",
        "8.2",
        ("Generated code and test fixtures are exempt.",),
    ),
    (
        "Coverage is a floor: a test that only raises it is noise.",
        "8.2",
        ("Coverage is a floor, not a goal. A test that only raises coverage is noise",),
    ),
    (
        "One concept per file, and tests mirror the source tree.",
        "8.5",
        ("One concept per file.", "Tests mirror the source tree."),
    ),
    (
        "Explicit over clever: no metaprogramming, reflection or dynamic dispatch that hides who"
        " calls what.",
        "8.5",
        (
            "**Explicit over clever.** No metaprogramming, reflection or dynamic dispatch that"
            " hides who calls what.",
        ),
    ),
    (
        "Names come from the product's vocabulary.",
        "8.5",
        ("Names come from the product's vocabulary",),
    ),
    (
        "Errors are typed, and unexpected data fails loudly instead of guessing a default.",
        "8.5",
        (
            "They are typed. Unexpected data fails loudly; nothing guesses a default for what it"
            " doesn't know.",
        ),
    ),
    (
        "No dead or commented-out code.",
        "8.5",
        ("No dead or commented-out code.",),
    ),
    (
        "A new dependency is the owner's decision.",
        "8.5",
        ("adding one needs an ADR (it is also high risk, §9.1)",),
    ),
    (
        "Components log their state changes and errors as structured records, never with secrets"
        " or personal data.",
        "8.5",
        (
            "Every component logs its state changes and errors as structured records",
            "Logs never hold secrets or personal data.",
        ),
    ),
    (
        "The PR body shows what you ran and what it returned.",
        "7.6",
        ("The PR shows what was run and what it returned",),
    ),
]


def one_line(text: str) -> str:
    """The text on one line, so that a check doesn't depend on wrapping."""
    return re.sub(r"\s+", " ", text)


def spec_section(number: str) -> str:
    """SPEC's section `number` (such as "7.1" or "5"), up to the next heading of its level."""
    text = SPEC.read_text(encoding="utf-8")
    marks = "###" if "." in number else "##"
    start = text.index(f"\n{marks} {number}. " if marks == "##" else f"\n{marks} {number} ")
    end = text.find(f"\n{marks} ", start + 1)
    return one_line(text[start : end if end != -1 else len(text)])


def prompt_rules() -> list[str]:
    """The sentences of the bulleted rules the prompt quotes, without their bold labels."""
    text = PROMPT.read_text(encoding="utf-8")
    start = text.index("## The rules")
    end = text.index("\n## ", start + 1)
    bullets = [line for line in text[start:end].splitlines() if line.startswith("- **")]
    sentences: list[str] = []
    for bullet in bullets:
        rule = re.sub(r"^- \*\*[^*]+\*\* ", "", bullet)
        sentences.extend(re.split(r"(?<=\.)\s+", rule.strip()))
    return sentences


@pytest.mark.parametrize(
    ("quote", "section", "sources"), QUOTES, ids=[f"§{s} {q[:40]}" for q, s, _ in QUOTES]
)
def test_a_quoted_rule_and_its_spec_source_change_together(
    quote: str, section: str, sources: tuple[str, ...]
) -> None:
    rules = prompt_rules()
    spec = spec_section(section)
    for source in sources:
        message = (
            f"The cloud prompt's rule {quote!r} quotes SPEC §{section}'s {source!r},"
            " and one of them changed: change the other to match, and this pair."
        )
        assert quote in rules, message
        assert one_line(source) in spec, message


def test_every_rule_the_cloud_prompt_quotes_has_its_spec_source() -> None:
    paired = {quote for quote, _, _ in QUOTES}
    unpaired = [rule for rule in prompt_rules() if rule not in paired]
    assert not unpaired, (
        f"The cloud prompt quotes rules with no SPEC source in this test: {unpaired}."
        " Add each to QUOTES with the SPEC text it comes from."
    )
