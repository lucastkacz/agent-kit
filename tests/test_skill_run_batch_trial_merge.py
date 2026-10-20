"""How run-batch trial-merges the waiting PRs and tells the owner how the batch goes (#150)."""

from __future__ import annotations

from run_batch_skill import TRIAL, section, skill_text


def test_the_batch_end_merges_the_waiting_prs_on_trial_in_a_scratch_worktree() -> None:
    trial = section(skill_text(), TRIAL)
    assert "When the whole batch ended" in trial, trial
    assert "in the plan's order" in trial, trial
    assert "the tracking issue's Notes" in trial, trial
    assert (
        "git worktree add --detach .agent-batch/worktrees.noindex/trial-<batch> origin/master"
        in trial
    )
    assert "`make check` after each" in trial, trial
    assert "git worktree remove --force .agent-batch/worktrees.noindex/trial-<batch>" in trial, (
        trial
    )


def test_a_pr_that_conflicts_or_fails_is_updated_and_shipped_before_the_owner_names_them() -> None:
    trial = section(skill_text(), TRIAL)
    conflicts = trial.index("conflicts or fails")
    up_to_date = trial.index("git merge origin/master", conflicts)
    ship_again = trial.index("agent-batch ship <n>", up_to_date)
    assert conflicts < up_to_date < ship_again, trial
    text = skill_text()
    assert text.index(f"## {TRIAL}") < text.index("## Next step"), text
    next_step = section(skill_text(), "Next step")
    assert "Only once the trial merged every waiting PR cleanly" in next_step, next_step
    assert "accept-batch" in next_step, next_step


def test_the_owner_asking_how_it_goes_gets_agent_batch_status_beside_the_cloud_runs() -> None:
    watch = section(skill_text(), "Watch")
    assert "When the owner asks how the batch is going" in watch, watch
    assert "run `agent-batch status` and show its rows" in watch, watch
    assert "with the cloud runs beside them" in watch, watch
