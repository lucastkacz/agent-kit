"""What tests of `agent-batch ship` share: a branch to ship, a remote that moves on, and its PR."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import World, git


def branch_with_work(world: World, branch: str, file: str = "feature.txt") -> Path:
    git(world.project, "switch", "--quiet", "--create", branch)
    path = world.project / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: work")
    body = world.root / "body.md"
    body.write_text("Adds the feature.\n")
    return body


def master_moves_on_the_remote(world: World) -> str:
    """Another clone pushes to `master`; returns the remote's new `master`."""
    other = world.root / "other"
    git(world.root, "clone", "--quiet", str(world.origin), str(other))
    (other / "later.txt").write_text("later\n")
    git(other, "add", "-A")
    git(other, "commit", "--quiet", "-m", "feat: later work on master")
    git(other, "push", "--quiet", "origin", "HEAD:master")
    return git(world.origin, "rev-parse", "master").strip()


def only_pr(world: World) -> dict[str, Any]:
    prs = list(world.gh()["prs"].values())
    assert len(prs) == 1, prs
    pr: dict[str, Any] = prs[0]
    return pr
