"""A batch keeps any computer awake, or says it can't, and nothing assumes a Mac (#52)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

from conftest import World

BATCH = 1
KIT = Path(__file__).parent.parent
# "Mac" as a word, as in "the Mac", "a Mac's" or "MacBook"; "macOS" names a platform.
MAC = re.compile(r"\bMac(Book)?\b", re.IGNORECASE)


def _run_one_issue(world: World) -> int:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\n")
    return world.run("run", str(BATCH))


@pytest.fixture
def linux(world: World, monkeypatch: pytest.MonkeyPatch) -> World:
    monkeypatch.setattr(sys, "platform", "linux")
    world.linux_power(mains_online=True)
    return world


def test_on_linux_a_batch_holds_off_idle_and_system_sleep_with_systemd_inhibit(
    linux: World,
) -> None:
    assert _run_one_issue(linux) == 0

    [flags] = linux.systemd_inhibit_calls()
    assert "--what=idle:sleep" in flags, "idle and system sleep aren't both held off"
    assert "--mode=block" in flags
    assert any(flag.endswith(str(os.getpid())) for flag in flags), "it doesn't last the batch"


def test_on_linux_a_computer_whose_mains_supply_is_offline_gets_the_battery_warning(
    linux: World, capsys: pytest.CaptureFixture[str]
) -> None:
    linux.linux_power(mains_online=False)

    assert _run_one_issue(linux) == 0

    said = capsys.readouterr().out.lower()
    assert "battery" in said
    assert "may sleep" in said
    assert "plugged in" in said


def test_on_linux_a_computer_on_mains_power_gets_no_battery_warning(
    linux: World, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run_one_issue(linux) == 0

    assert "battery" not in capsys.readouterr().out.lower()


def test_where_no_keep_awake_tool_exists_the_batch_says_so_at_the_start_and_still_runs(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "platform", "freebsd14")

    assert _run_one_issue(world) == 0

    said = capsys.readouterr().out
    assert "can't keep the computer awake" in said
    assert said.index("can't keep the computer awake") < said.index("issue_started")
    [pr] = world.gh()["prs"].values()
    assert pr["armed"], "the batch should have run anyway"


def _kit_texts() -> list[Path]:
    plugin = [path for path in (KIT / "plugin").rglob("*") if path.is_file()]
    texts = [path for path in plugin if "__pycache__" not in path.parts]
    return [*texts, KIT / "README.md", KIT / "SPEC.md"]


def test_no_message_comment_or_doc_in_the_kit_says_the_mac() -> None:
    found = [
        f"{path.relative_to(KIT)}:{number}: {line.strip()}"
        for path in _kit_texts()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if MAC.search(line)
    ]

    assert found == [], "these lines assume a Mac:\n" + "\n".join(found)
