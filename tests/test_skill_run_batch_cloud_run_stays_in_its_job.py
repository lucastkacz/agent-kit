"""A cloud run does only its job: no notification, artifact or file; its report ends it (#73)."""

from __future__ import annotations

from pathlib import Path

PROMPT = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "run-batch" / "cloud-prompt.md"


def prompt_text() -> str:
    return PROMPT.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_the_cloud_run_sends_no_notification_artifact_or_file() -> None:
    work = section(prompt_text(), "How to work")
    for word in ("`PushNotification`", "`Artifact`", "`SendUserFile`"):
        assert word in work, (word, work)
    assert "never notify the owner's phone" in work, work
    assert "publish an artifact" in work, work
    assert "send a file" in work, work


def test_the_control_tower_tells_the_owner_what_needs_them() -> None:
    work = section(prompt_text(), "How to work")
    assert "the control tower tells the owner what needs them" in work, work


def test_the_cloud_run_ends_with_its_report_as_its_final_answer() -> None:
    answer = section(prompt_text(), "Your final answer")
    assert "The run ends with this report as its final answer" in answer, answer
