"""`agent-batch ship` reviews against the remote's latest base (#39, medium tests)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_batch.core.model import ClaudeRun
from agent_batch.shell.claude import Claude
from conftest import World, git
from ship_branches import branch_with_work, master_moves_on_the_remote


def test_ship_fetches_the_remote_before_the_review(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")
    latest = master_moves_on_the_remote(world)
    seen: list[str] = []
    review = Claude.review

    def spy(self: Claude, cwd: Path, prompt: str) -> ClaudeRun:
        seen.append(git(cwd, "rev-parse", "origin/master").strip())
        return review(self, cwd, prompt)

    monkeypatch.setattr(Claude, "review", spy)

    assert world.run("ship", "10", "--title", "feat: x", "--body-file", str(body)) == 0
    assert seen == [latest]
