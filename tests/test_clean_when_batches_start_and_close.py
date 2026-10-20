"""A batch's start and its closing run `agent-batch clean`, and SPEC §5 says so (#111).

The run is a medium test, with real git and fake `gh` and `claude`; the others check the text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from accept_batch_skill import section
from batch_runs import events
from clean_branches import local_branches
from conftest import World, git

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"
HIGH_RISK_BRANCH = "10-issue-10"


def owner_merges(world: World, branch: str) -> None:
    """The owner merges the branch's waiting PR on GitHub, at the head the lane pushed."""
    head = git(world.project, "rev-parse", branch).strip()
    gh = world.gh()
    pr = next(pr for pr in gh["prs"].values() if pr["branch"] == branch)
    pr["state"], pr["head"] = "MERGED", head
    world.gh_state.write_text(json.dumps(gh))


def test_a_batch_run_deletes_at_its_start_a_branch_the_owner_merged_after_its_lane_ended(
    world: World,
) -> None:
    world.add_issue(10, risk="High")
    world.add_batch(1, "Lane 1: #10\n")
    world.run("run", "1")
    assert HIGH_RISK_BRANCH in local_branches(world), "the high-risk PR's branch waits"
    owner_merges(world, HIGH_RISK_BRANCH)
    world.add_issue(11)
    world.add_batch(2, "Lane 1: #11\n")

    assert world.run("run", "2") == 0

    assert HIGH_RISK_BRANCH not in local_branches(world)
    logged = events(world, 2)
    names = [str(event["event"]) for event in logged]
    about = [i for i, event in enumerate(logged) if event.get("branch") == HIGH_RISK_BRANCH]
    assert about, f"batch 2's log says nothing about {HIGH_RISK_BRANCH}: {names}"
    assert about[0] < names.index("issue_started"), names


def test_the_accept_batch_skill_runs_agent_batch_clean_when_it_closes_a_batch() -> None:
    closing = section("Record the acceptance")
    assert "agent-batch clean" in closing, closing


def step_8() -> str:
    """SPEC §5's step 8 in lowercase, on one line, so that a check doesn't depend on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("8. **Cleanup.**")
    end = text.index("\n\n", start)
    return re.sub(r"\s+", " ", text[start:end]).lower()


def test_spec_5_step_8_says_who_deletes_a_branch_whose_pr_merged_after_its_lane_ended() -> None:
    step = step_8()
    for token in (
        "after its lane ended",
        "`agent-batch clean`",
        "`agent-batch run`",
        "closes a batch",
    ):
        assert token in step, (token, step)
