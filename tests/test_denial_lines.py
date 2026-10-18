"""A denial's line in the batch summary: inert, short and bounded (#30's review, small tests)."""

from __future__ import annotations

import re

from hypothesis import assume, given
from hypothesis import strategies as st

from agent_batch.core import report
from agent_batch.core.model import Denial, IssueReport, Outcome, RunDenial

BACKTICK_RUNS = re.compile(r"`+")
PREFIX = "- #10 review: Bash "


def _summary(*denials: RunDenial) -> str:
    return report.render([IssueReport(10, Outcome.MERGED, denials=list(denials))], 60)


def _bash(command: str) -> RunDenial:
    return RunDenial("review", Denial("Bash", {"command": command}))


def test_a_command_with_backticks_mentions_and_references_stays_one_code_span() -> None:
    command = 'git commit -m "fix `foo` (#12) for @someone"'
    text = _summary(RunDenial("implementation", Denial("Bash", {"command": command})))

    assert f"- #10 implementation: Bash ``{command}``" in text


def test_a_command_that_starts_with_a_backtick_is_padded_inside_its_fence() -> None:
    assert f"{PREFIX}`` `date` ``" in _summary(_bash("`date`"))


def test_a_plain_command_keeps_single_backticks() -> None:
    assert f"{PREFIX}`git push origin HEAD`" in _summary(_bash("git push origin HEAD"))


@given(st.text(min_size=1, max_size=report.COMMAND_CHARS))
def test_any_command_comes_back_whole_from_its_code_span(command: str) -> None:
    flat = " ".join(command.splitlines())
    assume(flat)
    line = next(ln for ln in _summary(_bash(command)).splitlines() if ln.startswith(PREFIX))
    span = line.removeprefix(PREFIX)
    fence = span[: len(span) - len(span.lstrip("`"))]
    inner = span[len(fence) : -len(fence)]
    if flat.startswith("`") or flat.endswith("`"):
        inner = inner[1:-1]

    assert len(fence) > max((len(run) for run in BACKTICK_RUNS.findall(flat)), default=0)
    assert inner == flat


def test_a_denied_write_shows_its_path_and_never_its_content() -> None:
    write = Denial("Write", {"file_path": "notas.md", "content": "a secret line"})
    text = _summary(RunDenial("implementation", write))

    assert "- #10 implementation: Write `notas.md`" in text
    assert "a secret line" not in text


def test_another_tools_input_keeps_its_non_ascii_text() -> None:
    search = Denial("WebSearch", {"query": "acción"})
    text = _summary(RunDenial("implementation", search))

    assert '"query": "acción"' in text


def test_the_summary_lists_at_most_100_denials_and_points_to_the_event_log() -> None:
    text = _summary(*(_bash(f"echo {n}") for n in range(130)))

    assert sum(line.startswith(PREFIX) for line in text.splitlines()) == report.DENIAL_LINES
    assert "- … and 30 more in the batch's event log (`events.jsonl`)" in text
