"""`agent-batch ship` reviews against the remote's latest base (#39, medium tests)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_batch.core.model import ClaudeRun
from agent_batch.shell.claude import Claude
from conftest import World, git
from test_ship import branch_with_work


def master_moves_on_the_remote(world: World) -> str:
    """Another clone pushes to `master`; returns the remote's new `master`."""
    other = world.root / "other"
    git(world.root, "clone", "--quiet", str(world.origin), str(other))
    (other / "later.txt").write_text("later\n")
    git(other, "add", "-A")
    git(other, "commit", "--quiet", "-m", "feat: later work on master")
    git(other, "push", "--quiet", "origin", "HEAD:master")
    return git(world.origin, "rev-parse", "master").strip()


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
