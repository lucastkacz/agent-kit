"""Keep-awake and the battery check where the platform's tool or data is missing (#52)."""

from __future__ import annotations

import pytest

from agent_batch.shell import system
from conftest import World


@pytest.mark.parametrize("platform", ["darwin", "linux"])
def test_without_its_platforms_tool_the_computer_isnt_kept_awake(
    world: World, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    monkeypatch.setenv("PATH", str(world.root / "nothing"))

    assert system.keep_awake(platform) is None


def test_a_computer_that_lists_no_power_supply_counts_as_not_on_battery(world: World) -> None:
    world.power_supplies.mkdir()

    assert not system.on_battery("linux")


def test_a_battery_alone_without_a_mains_supply_counts_as_not_on_battery(world: World) -> None:
    world.linux_power(mains_online=False)
    for name in ("type", "online"):
        (world.power_supplies / "AC" / name).unlink()
    (world.power_supplies / "AC").rmdir()

    assert not system.on_battery("linux")


def test_a_mains_supply_that_cant_be_read_counts_as_not_on_battery(world: World) -> None:
    world.linux_power(mains_online=False)
    (world.power_supplies / "AC" / "online").unlink()

    assert not system.on_battery("linux")


def test_another_platform_counts_as_not_on_battery(world: World) -> None:
    world.linux_power(mains_online=False)

    assert not system.on_battery("freebsd14")
