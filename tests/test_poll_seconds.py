"""`AGENT_BATCH_POLL_SECONDS` must be a number above 0 (#26)."""

from __future__ import annotations

import pytest

from agent_batch import cli
from conftest import World

BATCH = 12


@pytest.mark.parametrize("seconds", ["abc", "0", "-1"])
def test_a_poll_interval_that_is_not_a_number_above_zero_stops_the_batch_with_an_error(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    seconds: str,
) -> None:
    world.add_batch(BATCH, "Lane 1: #10\n")
    monkeypatch.setenv("AGENT_BATCH_POLL_SECONDS", seconds)

    code = world.run("run", str(BATCH))

    assert code == 1
    assert world.gh()["calls"] == []
    err = capsys.readouterr().err
    assert "AGENT_BATCH_POLL_SECONDS" in err
    assert f"needs a number above 0, not {seconds!r}" in err
    assert "Traceback" not in err


def test_a_valid_poll_interval_is_the_poll_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_BATCH_POLL_SECONDS", "0.5")

    assert cli._config().poll_seconds == 0.5
