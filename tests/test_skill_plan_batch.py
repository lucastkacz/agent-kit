"""The plan-batch skill plans a batch with the owner, in the steps the owner approved (#57)."""

from __future__ import annotations

from pathlib import Path

from test_skills import frontmatter
from test_skills import test_each_skill_is_well_formed as check_well_formed

SKILL = Path(__file__).resolve().parents[1] / "plugin" / "skills" / "plan-batch"


def text() -> str:
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_the_skill_exists_and_is_well_formed() -> None:
    assert (SKILL / "SKILL.md").is_file(), f"{SKILL} has no SKILL.md"
    check_well_formed(SKILL)
    fields = frontmatter(SKILL)
    assert "disable-model-invocation" not in fields
    description = fields["description"].lower()
    for trigger in ("plan", "next", "idea"):
        assert trigger in description, f"the description doesn't trigger on {trigger!r}"
    assert "${user_config.language}" in text()


def test_it_starts_from_open_issues_blocked_issues_and_a_pending_acceptance() -> None:
    skill = text()
    assert "open issues without `ready`" in skill
    assert "`blocked` issues" in skill
    assert "acceptance is pending" in skill


def test_it_says_how_to_form_lanes() -> None:
    skill = text()
    assert "touch the same files share a lane" in skill
    assert "high-risk issue goes last in its lane, or alone" in skill
    assert "every issue is high risk, one per lane" in skill
    assert "`Lanes:` is the number of independent lanes" in skill


def test_it_proposes_the_cloud_and_the_model_with_the_owners_settings_as_default() -> None:
    skill = text()
    assert "`Cloud: #a, #b`" in skill
    assert "`Model: <model>, <effort>`" in skill
    assert "`model` and `effortLevel`" in skill
    assert "as the default" in skill


def test_it_labels_ready_only_after_one_approval_and_sets_up_the_batch() -> None:
    skill = text()
    approval = skill.index("One approval")
    milestone = skill.index("milestone named")
    tracking = skill.index("tracking issue labeled `batch`")
    ready = skill.index("only then label them `ready`")
    assert approval < milestone < tracking < ready
    assert "Acceptance checklist" in skill
    assert "Without `ready`" in skill or "without `ready`" in skill


def test_it_ends_by_asking_whether_to_start_the_batch_with_run_batch() -> None:
    last_section = text().rsplit("\n## ", 1)[-1]
    assert "whether to start the batch" in last_section
    assert "`run-batch`" in last_section
