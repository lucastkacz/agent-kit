"""`agent-batch run` refuses a budget that can't run (#20)."""

from __future__ import annotations

import pytest

from conftest import World

BATCH = 12


def _usage_error(world: World, capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    world.add_batch(BATCH, "Lane 1: #10\n")

    with pytest.raises(SystemExit) as exited:
        world.run("run", str(BATCH), *argv)

    assert exited.value.code == 2
    assert world.gh()["calls"] == []
    return capsys.readouterr().err.splitlines()[-1]


@pytest.mark.parametrize("count", ["0", "-1"])
def test_the_max_issues_flag_refuses_a_count_under_one(
    world: World, capsys: pytest.CaptureFixture[str], count: str
) -> None:
    error = _usage_error(world, capsys, "--max-issues", count)

    assert "--max-issues" in error
    assert repr(count) in error


@pytest.mark.parametrize("hours", ["0", "-1", "-0.5"])
def test_the_max_hours_flag_refuses_hours_that_are_not_above_zero(
    world: World, capsys: pytest.CaptureFixture[str], hours: str
) -> None:
    error = _usage_error(world, capsys, "--max-hours", hours)

    assert "--max-hours" in error
    assert repr(hours) in error


@pytest.mark.parametrize("hours", ["abc", "nan"])
def test_the_max_hours_flag_refuses_text_that_is_not_a_number_above_zero(
    world: World, capsys: pytest.CaptureFixture[str], hours: str
) -> None:
    error = _usage_error(world, capsys, "--max-hours", hours)

    assert f"needs a number above 0, not {hours!r}" in error
