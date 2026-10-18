"""After its review, run-batch takes only the owner's issues and sends a whole prompt (#58)."""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "run-batch"


def skill_text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def prompt_text() -> str:
    return (SKILL / "cloud-prompt.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_the_check_before_starting_requires_what_the_runner_requires() -> None:
    check = section(skill_text(), "Check before starting")
    assert "gh api user --jq .login" in check, check
    assert "labels,state,author,body" in check, check
    for word in ("`OPEN`", "opened by the owner", "`ready`", "`blocked`", "### Risk"):
        assert word in check, (word, check)
    assert "labeled `batch`" in check, check


def test_the_cloud_prompt_needs_no_file_of_the_kit_in_the_project() -> None:
    text = prompt_text()
    assert "{implement}" in text
    assert "SPEC.md" not in text
    assert "plugin/skills/" not in text


def test_the_skill_fills_the_prompt_from_the_plugins_own_files() -> None:
    fill = section(skill_text(), "Send an issue to the cloud")
    assert "`{implement}`" in fill, fill
    assert "${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md" in fill, fill


def test_the_cloud_answer_gives_its_status_and_the_work_it_found() -> None:
    answer = section(prompt_text(), "Your final answer")
    assert "**Status:**" in answer, answer
    assert "**Found:**" in answer, answer


def test_it_ships_the_branch_it_dispatched_at_the_head_the_run_reported() -> None:
    back = section(skill_text(), "Bring a cloud branch back")
    assert "the `{branch}` you dispatched" in back, back
    assert "`git rev-parse origin/<branch>` equals the head SHA" in back, back
    assert "--title '<title>'" in back, back
    assert "git worktree remove .agent-batch/worktrees/ship-<n>" in back, back
