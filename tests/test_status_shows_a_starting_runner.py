"""`agent-batch status` shows a batch's runner from its start, before any lane starts (#217)."""

from __future__ import annotations

import pytest

from agent_batch import batch
from agent_batch.core.model import IssueReport
from conftest import World

BATCH = 1


def test_before_any_lane_starts_an_issue_status_shows_the_batch_with_its_runner_and_no_lanes(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    shown: list[str] = []

    def no_issue_yet(*_: object) -> list[IssueReport]:
        capsys.readouterr()
        assert world.run("status") == 0
        shown.append(capsys.readouterr().out)
        return []

    monkeypatch.setattr(batch, "run_lane", no_issue_yet)

    assert world.run("run", str(BATCH)) == 0

    [table] = shown
    header, *rows = table.splitlines()
    assert header.startswith("RUN")
    assert [row.split("  ")[0] for row in rows] == [f"batch-{BATCH}, runner"]
    assert ", lane " not in table
