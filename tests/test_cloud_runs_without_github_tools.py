"""A cloud run gets none of GitHub's tools, and the SPEC says what keeps it from merging (#71)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugin" / "skills" / "run-batch" / "SKILL.md"
SPEC = ROOT / "SPEC.md"
GITHUB_TOOLS = "`mcp__github__*`"


def between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    return text[begin : text.index(end, begin + len(start))]


def test_run_batch_creates_every_routine_with_githubs_tools_disallowed() -> None:
    dispatch = between(SKILL.read_text(encoding="utf-8"), "## Send an issue to the cloud", "\n## ")

    assert "`disallowed_tools`" in dispatch, dispatch
    assert GITHUB_TOOLS in dispatch, dispatch
    assert "don't send" in dispatch, dispatch


def test_the_spec_says_what_keeps_a_cloud_run_from_merging() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    cloud = between(spec, "### 12.1", "\n## 13.")
    who = between(spec, "### 9.2", "### 9.3")

    assert GITHUB_TOOLS in cloud, cloud
    assert "disallow" in cloud, cloud
    assert "as the owner" in cloud, cloud
    assert "cloud run" in who, who
    assert "§12.1" in who, who
