"""The reviewer reads issues, pull requests and the API, and still can't write to GitHub (#72)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_batch.shell import claude

REVIEW_SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "review" / "SKILL.md"


def reviewer_tools() -> tuple[list[str], list[str]]:
    """The reviewer's allowed and denied tools, as its command line passes them to claude."""
    line = claude.command("Review issue #1.", {}, claude.REVIEWER)
    allowed = line[line.index("--allowedTools") + 1 : line.index("--disallowedTools")]
    denied = line[line.index("--disallowedTools") + 1 :]
    return allowed, denied


def test_the_reviewer_lists_issues_reads_trees_and_gh_reads_but_never_runs_gh_pr_or_api() -> None:
    allowed, denied = reviewer_tools()
    line = claude.command("Review issue #1.", {}, claude.REVIEWER)
    settings = Path(line[line.index("--settings") + 1])
    batch_deny = json.loads(settings.read_text(encoding="utf-8"))["permissions"]["deny"]

    assert "Bash(gh issue list *)" in allowed
    assert "Bash(git ls-tree *)" in allowed
    assert "Bash(agent-batch gh-read *)" in allowed
    assert {"Bash(gh pr *)", "Bash(gh api *)"} <= set(denied)
    assert {"Bash(gh pr *)", "Bash(gh api *)"} <= set(batch_deny)


def test_the_review_skill_names_the_commands_it_has_for_reading_github() -> None:
    text = REVIEW_SKILL.read_text(encoding="utf-8")

    for command in (
        "gh issue view",
        "gh issue list",
        "git ls-tree",
        "agent-batch gh-read pr view",
        "agent-batch gh-read pr list",
        "agent-batch gh-read pr diff",
        "agent-batch gh-read pr checks",
        "agent-batch gh-read api",
    ):
        assert command in text, f"the review skill doesn't name `{command}`"


def test_the_review_skill_says_gh_read_refuses_web_on_pull_requests() -> None:
    text = REVIEW_SKILL.read_text(encoding="utf-8")
    pull_requests = next(line for line in text.splitlines() if "Pull requests:" in line)

    assert "`--web`/`-w`" in pull_requests
    assert "refuses" in pull_requests
