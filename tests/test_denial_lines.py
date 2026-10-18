"""A denial's line in the batch summary stays one inert code span (#30's review, small tests)."""

from __future__ import annotations

from agent_batch.core import report
from agent_batch.core.model import Denial, IssueReport, Outcome, RunDenial


def _summary(*denials: RunDenial) -> str:
    return report.render([IssueReport(10, Outcome.MERGED, denials=list(denials))], 60)


def test_a_command_with_backticks_mentions_and_references_stays_one_code_span() -> None:
    command = 'git commit -m "fix `foo` (#12) for @someone"'
    text = _summary(RunDenial("implementation", Denial("Bash", {"command": command})))

    assert f"- #10 implementation: Bash ``{command}``" in text


def test_a_command_that_starts_with_a_backtick_is_padded_inside_its_fence() -> None:
    text = _summary(RunDenial("review", Denial("Bash", {"command": "`date`"})))

    assert "- #10 review: Bash `` `date` ``" in text


def test_a_plain_command_keeps_single_backticks() -> None:
    text = _summary(RunDenial("review", Denial("Bash", {"command": "git push origin HEAD"})))

    assert "- #10 review: Bash `git push origin HEAD`" in text


def test_another_tools_input_keeps_its_non_ascii_text() -> None:
    write = Denial("Write", {"file_path": "notas.md", "content": "acción"})
    text = _summary(RunDenial("implementation", write))

    assert '"content": "acción"' in text
