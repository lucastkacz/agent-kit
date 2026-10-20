"""What tests of a branch's review rounds share: findings, and shipping a branch round by round."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import World, git


def finding(severity: str, origin: str, location: str, problem: str) -> dict[str, str]:
    return {
        "severity": severity,
        "origin": origin,
        "location": location,
        "problem": problem,
        "suggestion": f"Fix what {location} does.",
    }


def changes(*findings: dict[str, str]) -> dict[str, Any]:
    return {"output": {"verdict": "changes", "findings": list(findings)}}


DROPS_A_LINE = finding("medium", "new", "a.py:3", "It drops the last line.")
CRASHES = finding("high", "new", "b.py:7", "It crashes on an empty file.")
SLOW = finding("medium", "new", "c.py:12", "It reads the file twice.")


def start_branch(world: World) -> Path:
    git(world.project, "switch", "--quiet", "--create", "10-add-feature")
    commit(world, "feature.txt")
    body = world.root / "body.md"
    body.write_text("Adds the feature.\n")
    return body


def commit(world: World, file: str) -> None:
    (world.project / file).write_text(f"{file}\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", f"fix: {file}")


def ship(world: World, body: Path) -> int:
    return world.run("ship", "10", "--title", "feat: add the feature", "--body-file", str(body))


def ship_rounds(world: World, *reviews: dict[str, Any]) -> list[int]:
    """Ships the branch once per review, with a fix committed before each re-review."""
    world.add_issue(10)
    world.script("review", 10, *reviews)
    body = start_branch(world)
    codes = []
    for index in range(len(reviews)):
        if index:
            commit(world, f"fix_{index}.txt")
        codes.append(ship(world, body))
    return codes
