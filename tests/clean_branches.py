"""What tests of `agent-batch clean` share: its run, the branches it may delete and their PRs."""

from __future__ import annotations

import json

from agent_batch import cli
from conftest import World, git

MERGED = "51-a-resumed-run-that-s-replaced-loses-its"
OTHER = "66-re-running-a-batch-skips-a-merged-issue"


def clean() -> int:
    """`agent-batch clean`'s exit code, also when argparse exits on a usage error."""
    try:
        return cli.main(["clean"])
    except SystemExit as exited:
        return int(exited.code or 0)


def branch_with_work(world: World, name: str) -> str:
    """A local branch one commit ahead of master, as a lane leaves it; returns its head."""
    git(world.project, "switch", "--quiet", "--create", name)
    (world.project / f"{name}.txt").write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", f"feat: {name}")
    git(world.project, "switch", "--quiet", "master")
    return git(world.project, "rev-parse", name).strip()


def add_pr(world: World, number: int, branch: str, *, state: str, head: str) -> None:
    """A PR on the branch, in the given state, whose head on GitHub is `head`."""
    gh = world.gh()
    gh["prs"][str(number)] = {
        "number": number,
        "branch": branch,
        "base": "master",
        "title": "feat: a thing",
        "body": "Closes #10",
        "state": state,
        "labels": [],
        "comments": [],
        "armed": None,
        "views": [],
        "head": head,
    }
    world.gh_state.write_text(json.dumps(gh))


def local_branches(world: World) -> list[str]:
    return git(world.project, "branch", "--format=%(refname:short)").split()


def said_about(out: str, branch: str) -> str:
    """The line of clean's output about the branch."""
    lines = [line for line in out.splitlines() if branch in line]
    assert len(lines) == 1, out
    return lines[0].lower()
