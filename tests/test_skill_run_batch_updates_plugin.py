"""run-batch updates the plugin before it starts, and its trial steps point right (#238).

Batch #219 ran whole on a plugin older than its marketplace's latest, and the trial's step 6
pointed to the wrong step of "Bring a cloud branch back". Each test checks the few words that
carry the behavior, so rewording the skill doesn't break it.
"""

from __future__ import annotations

from run_batch_skill import TRIAL, section, skill_text, step


def has(text: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, (missing, text)


def _plugin_check() -> str:
    checks = section(skill_text(), "Check before starting")
    has(checks, "claude plugin marketplace update")
    start = checks.index("claude plugin marketplace update")
    return checks[checks.rindex("\n- ", 0, start) : checks.index("\n- ", start)]


def test_the_check_before_starting_updates_the_marketplace_and_the_plugin_at_its_scope() -> None:
    check = _plugin_check()

    has(check, "claude plugin list --json", "`scope`")
    has(check, "`claude plugin marketplace update agent-kit`")
    has(check, "`claude plugin update agent-kit@agent-kit --scope <scope>`")
    has(check, "print each one's output")
    marketplace = check.index("claude plugin marketplace update")
    assert marketplace < check.index("claude plugin update agent-kit@agent-kit"), check


def test_a_changed_plugin_has_the_owner_reload_it_before_anything_starts() -> None:
    check = _plugin_check()

    has(check, "When the plugin changed", "`/reload-plugins`", "`claude --continue`")
    has(check, "start nothing", "until they have")


def test_a_resume_runs_the_plugin_check_except_while_a_runner_of_the_batch_still_runs() -> None:
    resume = section(skill_text(), "Resume")
    first = resume[resume.index("\n- ") : resume.index("\n- ", resume.index("\n- ") + 1)]

    has(first, "Update the plugin as in the checks before starting")

    update = first.index("Update the plugin")
    assert "no runner of the batch is still running" in first[update:], first


def test_trial_step_6_points_to_the_cloud_branchs_step_that_makes_its_worktree() -> None:
    six = step(section(skill_text(), TRIAL), 6)

    has(six, 'make or reuse that worktree as in "Bring a cloud branch back" step 2')
    assert '"Bring a cloud branch back" step 3' not in six, six


def test_trial_step_2_removes_a_trial_worktree_left_in_the_old_folder() -> None:
    two = step(section(skill_text(), TRIAL), 2)

    has(two, "`.agent-batch/worktrees/`")
    old = two.index("`.agent-batch/worktrees/`")
    has(two[old - 200 : old + 200], "trial-<batch>", "git worktree remove --force")
    assert old < two.index("git worktree prune"), two
