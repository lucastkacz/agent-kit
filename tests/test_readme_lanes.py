"""The README shows that a batch runs its issues side by side, in lanes (#81)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERMAID = re.compile(r"^```mermaid[ \t]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def mermaid_diagrams() -> list[str]:
    return MERMAID.findall((ROOT / "README.md").read_text(encoding="utf-8"))


def test_a_readme_diagram_shows_lanes_side_by_side_and_the_cloud() -> None:
    diagrams = mermaid_diagrams()
    lanes = [
        diagram
        for diagram in diagrams
        if all(lane in diagram for lane in ("Lane 1", "Lane 2", "Lane N"))
    ]
    assert lanes, (
        f'None of the README\'s {len(diagrams)} diagrams shows "Lane 1", "Lane 2" and "Lane N"'
    )
    assert any("cloud" in diagram.lower() for diagram in lanes), (
        "The README's lanes diagram doesn't show the cloud"
    )
