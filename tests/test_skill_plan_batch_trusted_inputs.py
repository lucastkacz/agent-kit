"""The plan-batch skill trusts only the owner's questions, skips cloud issues that wait for a fix, and writes a `Model:` line the runner takes (#70)."""

from __future__ import annotations

from agent_batch.core.plan import EFFORTS
from test_skill_plan_batch_rules import section


def model_bullet() -> str:
    """Step 4's bullet on the model, up to the example."""
    return section(4).split("- **The model.**", 1)[1].split("\n\n", 1)[0]


def test_a_blocked_issues_question_is_read_from_the_owners_latest_comment() -> None:
    start = section(1)
    assert "in each one's latest comment" not in start
    assert "their questions, in the owner's latest comment on each one" in start


def test_a_cloud_issue_that_waits_for_a_direct_mode_fix_is_left_out_of_the_plan() -> None:
    start = section(1)
    assert "its review asked for changes or its `ship` failed" in start
    assert "isn't left behind" in start
    assert "waits for a direct-mode fix in its kept worktree" in start
    assert "leave it out of the plan" in start


def test_the_model_line_is_written_only_when_the_owner_names_a_model() -> None:
    model = model_bullet()
    assert "Write a `Model:` line only when the owner names a model" in model
    assert "When the owner names no model, leave the line out" in model


def test_the_effort_is_added_only_when_the_runner_takes_it() -> None:
    model = model_bullet()
    levels = ", ".join(f"`{effort}`" for effort in EFFORTS[:-1]) + f" or `{EFFORTS[-1]}`"
    assert f"only when it's one of {levels}" in model
    assert "the runner refuses the batch" in model
