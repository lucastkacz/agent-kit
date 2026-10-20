"""run-batch sends only the owner's issues, with a whole prompt, and ships what it sent (#58)."""

from __future__ import annotations

from run_batch_skill import prompt_text, section, skill_text


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
    assert "named as the runner's `naming.branch_name` names it" in fill, fill


def test_each_routine_is_named_after_the_repository_the_batch_and_the_issue() -> None:
    name = "`<owner/name> batch <batch>: #<n>`"
    text = skill_text()
    assert name in section(text, "Send an issue to the cloud")
    assert name in section(text, "Resume")


def test_the_cloud_run_picks_up_a_branch_that_exists() -> None:
    work = section(prompt_text(), "How to work")
    assert "git ls-remote --exit-code --heads origin {branch}" in work, work
    assert "git fetch origin {branch}:refs/remotes/origin/{branch}" in work, work
    assert "--no-track origin/{branch}" in work, work


def test_the_issues_body_travels_between_tags() -> None:
    assert "<issue-body>\n{body}\n</issue-body>" in prompt_text()


def test_the_cloud_answer_gives_its_status_and_the_work_it_found() -> None:
    answer = section(prompt_text(), "Your final answer")
    assert "**Status:**" in answer, answer
    assert "**Found:**" in answer, answer


def test_it_ships_the_branch_it_dispatched_once_its_head_holds_the_pr() -> None:
    back = section(skill_text(), "Bring a cloud branch back")
    assert "the `{branch}` you dispatched" in back, back
    assert "`git diff --quiet origin/<branch>~1 origin/<branch>` exits 0" in back, back
    assert "--title '<title>'" in back, back
    assert "git worktree remove .agent-batch/worktrees.noindex/ship-<n>" in back, back
