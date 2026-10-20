"""A cloud branch comes back through git and a general-purpose subagent, not the run log (#151)."""

from __future__ import annotations

from run_batch_skill import prompt_text, section, skill_text, step


def test_the_run_pushes_its_pr_title_and_body_whole_as_its_branchs_head_commit() -> None:
    work = section(prompt_text(), "How to work")
    assert "git commit --allow-empty --cleanup=verbatim" in work, work
    assert "the PR's title" in work, work
    assert "the PR's body" in work, work
    answer = section(prompt_text(), "Your final answer")
    assert "**PR body:**" not in answer, answer
    assert "**PR title:**" not in answer, answer


def test_run_batch_reads_the_pr_title_and_body_from_git_not_from_the_run_log() -> None:
    back = section(skill_text(), "Bring a cloud branch back")
    assert "git log -1 --format=%s origin/<branch>" in back, back
    assert "git log -1 --format=%b origin/<branch>" in back, back
    log = step(back, 1)
    assert "title" not in log, log
    assert "body" not in log, log


def test_a_general_purpose_subagent_brings_each_branch_back_with_a_short_prompt() -> None:
    back = section(skill_text(), "Bring a cloud branch back")
    assert "general-purpose subagent" in back, back
    assert "short, self-contained prompt" in back, back
    assert "`fork`" not in back.split("general-purpose subagent", 1)[1], back


def test_a_fork_is_used_only_for_remote_trigger() -> None:
    paragraphs = skill_text().split("\n\n")
    forks = [p for p in paragraphs if "fork" in p.lower()]
    assert forks
    for paragraph in forks:
        assert "RemoteTrigger" in paragraph, paragraph


def test_step_6_removes_the_ship_worktree_and_leaves_the_branch_to_clean() -> None:
    removal = step(section(skill_text(), "Bring a cloud branch back"), 6)
    assert "git worktree remove .agent-batch/worktrees.noindex/ship-<n>" in removal, removal
    assert "git branch -d" not in removal, removal
    assert "`agent-batch clean`" in removal, removal
