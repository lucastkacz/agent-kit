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


def test_a_resume_sends_the_unfinished_lane_issues_to_the_next_batch() -> None:
    resume = section("Resume")
    assert "don't start the runner again" in resume, resume
    assert "go to the next batch" in resume, resume
    assert "`plan-batch`" in resume, resume


def test_a_resume_skips_the_cloud_issues_labeled_blocked() -> None:
    resume = section("Resume")
    assert "isn't labeled `blocked`" in resume, resume
    assert "aren't labeled `blocked`" in resume, resume


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
    assert "After the batch, the owner chooses" in back, back
    results = section("The cloud's results")
    assert "a review that asked for changes or a `ship` that failed" in results, results


def test_a_worktree_on_a_local_branch_gets_its_setup_and_a_bare_number_isnt_sent() -> None:
    back = section("Bring a cloud branch back")
    local = "`git worktree add .agent-batch/worktrees/ship-<n> <branch>`, then the same merge"
    assert f"{local}, and `make setup`" in back, back
    send = section("Send an issue to the cloud")
    assert "`naming.branch_name`" in send, send
    assert "just the number, which `agent-batch ship` refuses" in send, send
