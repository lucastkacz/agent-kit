"""`--max-hours` refuses text that isn't a number above 0 (#20)."""

from __future__ import annotations

import pytest

from conftest import World

BATCH = 12


@pytest.mark.parametrize("hours", ["abc", "nan"])
def test_the_max_hours_flag_refuses_text_that_is_not_a_number_above_zero(
    world: World, capsys: pytest.CaptureFixture[str], hours: str
) -> None:
    world.add_batch(BATCH, "Lane 1: #10\n")

    with pytest.raises(SystemExit) as exited:
        world.run("run", str(BATCH), "--max-hours", hours)

    assert exited.value.code == 2
    assert world.gh()["calls"] == []
    assert f"needs a number above 0, not {hours!r}" in capsys.readouterr().err
