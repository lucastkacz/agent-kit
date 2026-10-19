"""The `reviewed` event's plain line counts its findings; the JSON log keeps them (#105)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from agent_batch.core.model import Finding
from agent_batch.shell.events import EventLog

FIRST = Finding("high", "new", "a.py:1", "The parser drops the last line.", "Read to the end.")
SECOND = Finding("low", "earlier", "b.py:7", "The name says nothing.", "Call it `lanes`.")


def emit(tmp_path: Path, event: str, **fields: object) -> EventLog:
    log = EventLog(tmp_path / "run" / "events.jsonl")
    log.emit(event, **fields)
    return log


def test_a_reviewed_events_plain_line_counts_its_two_findings_without_their_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    emit(tmp_path, "reviewed", issue=10, findings=[asdict(FIRST), asdict(SECOND)])

    line = capsys.readouterr().out
    assert " findings=2" in line
    for text in ("The parser drops", "Read to the end", "The name says", "a.py:1", "b.py:7"):
        assert text not in line


def test_a_reviewed_events_plain_line_without_findings_shows_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    emit(tmp_path, "reviewed", issue=10, findings=[])

    assert " findings=0" in capsys.readouterr().out


def test_the_json_log_keeps_every_finding_of_a_reviewed_event(tmp_path: Path) -> None:
    log = emit(tmp_path, "reviewed", issue=10, findings=[asdict(FIRST), asdict(SECOND)])

    record = json.loads(log.path.read_text(encoding="utf-8"))
    assert record["findings"] == [
        {
            "severity": "high",
            "origin": "new",
            "location": "a.py:1",
            "problem": "The parser drops the last line.",
            "suggestion": "Read to the end.",
        },
        {
            "severity": "low",
            "origin": "earlier",
            "location": "b.py:7",
            "problem": "The name says nothing.",
            "suggestion": "Call it `lanes`.",
        },
    ]


def test_other_events_plain_lines_print_every_field_as_before(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    emit(tmp_path, "permission_denied", issue=10, findings=["kept"], input={"cmd": "rm"})

    line = capsys.readouterr().out
    assert line.endswith(" permission_denied issue=10 findings=['kept'] input={'cmd': 'rm'}\n")
