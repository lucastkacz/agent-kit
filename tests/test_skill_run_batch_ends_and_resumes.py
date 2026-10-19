"""How run-batch ends each cloud issue, and what it does on a resume (#58)."""

from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "run-batch" / "SKILL.md"
# The line the runner's `_announce` ends a blocked or failed issue's comment with.
SETTLED = "Once it's settled, remove the `blocked` label and the issue goes back to the next batch."


def section(heading: str) -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_a_resume_checks_only_the_cloud_issues_still_to_do_and_watches_the_runs_going_on() -> None:
    resume = section("Resume")
    assert "only on the `Cloud:` issues still to do" in resume, resume
    assert "keep those on the tracking issue and on `master`" in resume, resume
    assert "hasn't ended: watch it" in resume, resume
    assert "don't send its issue again" in resume, resume


def test_a_resume_starts_the_runner_again_when_none_is_still_running() -> None:
    resume = section("Resume")
    assert "is still running, watch it, as in Watch" in resume, resume
    assert "Otherwise, start `agent-batch run <batch>` again, as in Start" in resume, resume
    assert "don't start the runner again" not in resume, resume
    assert "go to the next batch" not in resume, resume


def test_the_watch_leaves_the_unfinished_lane_issues_to_a_resume() -> None:
    watch = section("Watch")
    assert "A resume starts it again for the lane issues it didn't finish" in watch, watch
    assert "go to the next batch" not in watch, watch


def test_a_resume_skips_the_cloud_issues_labeled_blocked() -> None:
    resume = section("Resume")
    assert "isn't labeled `blocked`" in resume, resume
    assert "aren't labeled `blocked`" in resume, resume


def test_a_resume_doesnt_ship_again_a_branch_whose_review_asked_for_changes() -> None:
    resume = section("Resume")
    assert "`approved` false, don't ship it again" in resume, resume
    assert "waits for a direct-mode fix" in resume, resume


def test_cloud_branches_come_back_one_at_a_time_retrying_a_lock_once() -> None:
    back = section("Bring a cloud branch back")
    assert "one branch at a time" in back, back
    assert "fails on a `.lock` file, retry it once" in back, back


def test_a_failed_cloud_run_is_labeled_blocked_with_the_runners_comment() -> None:
    back = section("Bring a cloud branch back")
    assert "gh issue edit <n> --add-label blocked" in back, back
    assert "**Blocked: this needs a decision from the owner.**" in back, back
    assert "**The batch couldn't finish this issue.**" in back, back
    assert SETTLED in back, back


def test_a_ship_that_asks_for_changes_or_fails_ends_the_issue_for_the_batch() -> None:
    back = section("Bring a cloud branch back")
    assert "`ship` fails" in back, back
    assert "has ended for this batch" in back, back
    assert "After the batch, fix it in this session" in back, back
    assert "in direct mode with the implement skill" in back, back
    assert "back to the cloud" not in back, back
    results = section("The cloud's results")
    assert "a review that asked for changes or a `ship` that failed" in results, results


def test_a_worktree_on_a_local_branch_gets_its_setup_and_a_bare_number_isnt_sent() -> None:
    back = section("Bring a cloud branch back")
    local = "`git worktree add .agent-batch/worktrees/ship-<n> <branch>`, then the same merge"
    assert f"{local}, and `make setup`" in back, back
    send = section("Send an issue to the cloud")
    assert "`naming.branch_name`" in send, send
    assert "just the number, which `agent-batch ship` refuses" in send, send
