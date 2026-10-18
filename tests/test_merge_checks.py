"""The session-start context carries the checks before a merge the owner asked for (#62)."""

from __future__ import annotations

import pytest

from conftest import World
from test_session_hooks import context


def test_the_session_names_the_checks_before_a_merge_and_the_pinned_merge_command(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = context(world, monkeypatch)

    assert "naming it by number" in text
    assert "it's open" in text
    assert "head hasn't changed" in text
    assert "CI is green" in text
    assert "no conflict" in text
    assert "`gh pr merge <n> --squash --match-head-commit <sha>`" in text
