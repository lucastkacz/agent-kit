"""Reading Claude Code's plugin validation (small tests)."""

from __future__ import annotations

from validate_plugin import problems


def warning(path: str) -> dict[str, str]:
    return {"path": path, "message": f"about {path}"}


def test_only_the_missing_version_is_let_through() -> None:
    report = {
        "manifest": {
            "errors": [],
            "warnings": [warning("version"), warning("plugins[0] plugin.json → version")],
        },
        "contents": [],
    }
    assert problems(report, "plugin") == []


def test_errors_and_other_warnings_count_wherever_they_are() -> None:
    report = {
        "manifest": {"errors": [{"path": "name", "message": "bad name"}], "warnings": []},
        "contents": [{"errors": [], "warnings": [warning("skills/review/SKILL.md")]}],
    }
    assert problems(report, "plugin") == [
        "plugin: error at name: bad name",
        "plugin: warning at skills/review/SKILL.md: about skills/review/SKILL.md",
    ]
