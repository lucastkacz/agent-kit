"""run-batch sends only the owner's issues, with a whole prompt, and ships what it sent (#58)."""

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


def test_no_issue_is_both_in_a_lane_and_in_the_cloud() -> None:
    check = section(skill_text(), "Check before starting")
    assert "both in a lane and on the `Cloud:` line" in check, check


def test_a_runner_that_may_outlast_the_tools_timeout_starts_in_a_terminal() -> None:
    start = section(skill_text(), "Start")
    assert "the longest `timeout`" in start, start
    assert "in a terminal" in start, start


def test_the_cloud_prompt_needs_no_file_of_the_kit_in_the_project() -> None:
    text = prompt_text()
    assert "{implement}" in text
    assert "SPEC.md" not in text
    assert "plugin/skills/" not in text


def test_the_skill_fills_the_prompt_from_the_plugins_own_files() -> None:
    fill = section(skill_text(), "Send an issue to the cloud")
    assert "`{implement}`" in fill, fill
    assert "${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md" in fill, fill
    assert "named as the runner names it" in fill, fill


def test_the_cloud_run_picks_up_a_branch_that_exists() -> None:
    work = section(prompt_text(), "How to work")
    assert "git ls-remote --exit-code --heads origin {branch}" in work, work
    assert "--no-track origin/{branch}" in work, work


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
