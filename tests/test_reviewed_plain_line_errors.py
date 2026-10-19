"""A `reviewed` event whose findings aren't a list fails loudly, not with a guess (#105)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_batch.shell.events import EventLog


def test_a_reviewed_event_with_a_count_for_findings_is_refused(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "run" / "events.jsonl")

    with pytest.raises(TypeError, match="must be a list"):
        log.emit("reviewed", issue=10, findings=2)
