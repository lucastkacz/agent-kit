"""The run-batch skill starts a batch and watches its lanes and the cloud (#58)."""

from __future__ import annotations

from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugin"
SKILL = PLUGIN / "skills" / "run-batch"


def skill_text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def prompt_text() -> str:
    return (SKILL / "cloud-prompt.md").read_text(encoding="utf-8")


def paragraph_with(text: str, needle: str) -> str:
    """The paragraph or list item of `text` that holds `needle`."""
    start = text.index(needle)
    begin = max(text.rfind("\n- ", 0, start), text.rfind("\n\n", 0, start), 0)
    ends = [end for end in (text.find("\n- ", start), text.find("\n\n", start)) if end != -1]
    return text[begin : min(ends) if ends else len(text)]


def test_the_skill_triggers_on_its_own_and_talks_in_the_owners_language() -> None:
    text = skill_text()
    head = text[: text.index("\n---\n", 4)]
    assert "name: run-batch" in head
    assert "disable-model-invocation" not in head
    for word in ("start", "run", "resume"):
        assert word in head.lower(), word
    assert "${user_config.language}" in text


def test_it_starts_the_runner_in_the_background_only_when_the_plan_has_lanes() -> None:
    text = skill_text()
    step = paragraph_with(text, "`agent-batch run <batch>`")
    assert "background" in step, step
    assert "only a `Cloud:` line" in step, step
    assert "isn't started" in step, step


def test_it_creates_one_one_time_routine_per_cloud_issue_and_clears_its_connectors() -> None:
    text = skill_text()
    assert "One routine per `Cloud:` issue" in text
    assert "`RemoteTrigger`" in text
    assert "`run_once_at`" in text
    assert "one-time" in text
    create = text.index("`create`")
    clear = text.index("`clear_mcp_connections: true`")
    assert create < clear
    assert "right after" in text[create - 200 : clear]


def test_the_cloud_prompt_has_its_placeholders_tests_first_and_a_push_but_no_pr() -> None:
    text = prompt_text()
    for placeholder in ("{repository}", "{number}", "{title}", "{body}", "{branch}"):
        assert placeholder in text, placeholder
    assert "--no-track" in text
    assert "acceptance tests first" in text.lower()
    assert "git push" in text
    assert "Never open a pull request" in text


def test_it_brings_each_cloud_branch_back_with_agent_batch_ship() -> None:
    text = skill_text()
    assert "`list_runs`" in text
    assert "`get_run_log`" in text
    assert "git worktree add .agent-batch/worktrees/ship-<n> -b <branch> origin/<branch>" in text
    assert "agent-batch ship <n> --title" in text


def test_it_names_exactly_the_four_cases_that_notify_the_owner() -> None:
    text = skill_text()
    start = text.index("## Notify")
    section = text[start : text.index("\n## ", start + 1)]
    cases = [line for line in section.splitlines() if line.startswith("- ")]
    assert len(cases) == 4, cases
    assert "`issue_finished` with `blocked`" in cases[0], cases[0]
    assert '`issue_set_aside` with "the batch stopped"' in cases[1], cases[1]
    assert "cloud run fails" in cases[2], cases[2]
    assert "whole batch" in cases[3], cases[3]
    assert "Never notify for each PR" in section, section


def test_it_comments_the_cloud_results_resumes_and_ends_asking_to_accept() -> None:
    text = skill_text()
    comment = paragraph_with(text, 'Comment "Cloud" on the tracking issue')
    for field in ("branch", "PR", "minutes", "outcome"):
        assert field in comment, (field, comment)
    start = text.index("## Resume")
    resume = text[start : text.index("\n## ", start + 1)]
    assert "continue" in resume, resume
    assert "no PR yet" in resume, resume
    last = text.rstrip().rsplit("\n## ", 1)[1]
    assert "`accept-batch`" in last, last
