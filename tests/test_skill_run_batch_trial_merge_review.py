"""How run-batch's trial merge answers its first review (#150).

Each test checks the few words that carry the behavior, so rewording the skill doesn't break it.
"""

from __future__ import annotations

from run_batch_skill import SKILL, TRIAL, section, skill_text

ACCEPT = SKILL.parent / "accept-batch" / "SKILL.md"


def has(text: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, (missing, text)


def test_only_a_pr_that_fails_on_master_alone_is_brought_up_to_date() -> None:
    trial = section(skill_text(), TRIAL)
    has(trial, "try it alone on master", "git switch --detach origin/master")
    has(trial, "fails only on top of an earlier waiting PR", "conflict or failing check alike")
    has(trial, "leave it out of the PRs the owner names now", "merges after the PRs before it")
    alone = trial.index("Bring each PR that fails on master alone up to date")
    assert trial.index("try it alone on master") < alone, trial
    assert alone < trial.index("git merge origin/master"), trial


def test_the_trial_runs_again_only_after_a_pr_was_brought_up_to_date_and_ends() -> None:
    trial = section(skill_text(), TRIAL)
    has(trial, "Run it again only when step 6 brought a PR up to date")
    has(trial, "bring each PR up to date at most once", "the trial ends")


def test_a_pr_is_brought_up_to_date_in_a_ship_worktree_made_as_for_a_cloud_branch() -> None:
    trial = section(skill_text(), TRIAL)
    has(trial, "a lane's PR too", "the runner removes a lane's worktree when the lane ends")
    has(trial, "git fetch origin <branch>", 'as in "Bring a cloud branch back" step 2')
    assert "the lane's worktree for a lane's" not in trial, trial
    assert "-b <branch>" not in trial, trial


def test_the_trial_comments_its_result_on_the_tracking_issue() -> None:
    trial = section(skill_text(), TRIAL)
    has(trial, "Comment the trial's result on the tracking issue", "`## Trial merge`")
    has(trial, "the PRs that merged cleanly, in the trial's order", "each PR left out, with why")
    assert trial.index("8. Comment the trial's result") > trial.index("7. "), trial


def test_accept_batch_builds_its_merge_command_from_the_trials_comment() -> None:
    text = ACCEPT.read_text(encoding="utf-8")
    start = text.index("### 2.2 ")
    step = text[start : text.index("\n### ", start + 1)]
    has(step, "starts with `## Trial merge`", "only the PRs it merged cleanly, in its order")
    has(step, "List each PR it left out apart", "`|| break` stops at the first PR")
    gather = text[text.index("## 1. Gather everything") : start]
    has(gather, "the latest comment that starts with `## Trial merge`")
