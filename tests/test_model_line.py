"""A batch runs on the model and effort its tracking issue names (#56)."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from agent_batch.core import plan
from agent_batch.core.plan import PlanError
from agent_batch.shell import claude
from conftest import World
from test_ship import branch_with_work

BATCH = 1
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DONE = {"status": "done", "title": "feat: a thing", "pr_body": "Body.", "message": "", "found": []}


def flag(argv: Sequence[str], name: str) -> str | None:
    """The value after a flag on a command line, or None when it isn't there."""
    if name not in argv:
        return None
    return argv[list(argv).index(name) + 1]


def test_every_run_of_the_batch_gets_the_model_and_effort_of_its_model_line(
    world: World,
) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\nModel: opus, max\n")
    world.script("implement", 10, {"output": DONE, "files": ["shared.txt"]})
    conflict = {"file": "shared.txt", "content": "another lane\n"}
    world.pr_views(
        "10-issue-10",
        {"state": "OPEN", "mergeable": "CONFLICTING", "push_conflict": conflict},
    )

    world.run("run", str(BATCH))

    calls = world.claude_calls()
    assert {call["kind"] for call in calls} == {"implement", "review", "resolve"}
    for call in calls:
        assert flag(call["argv"], "--model") == "opus", call["kind"]
        assert flag(call["argv"], "--effort") == "max", call["kind"]


def test_a_model_line_without_an_effort_sets_only_the_model() -> None:
    batch = plan.parse_plan("Lane 1: #1\nModel: sonnet\n")
    assert (batch.model, batch.effort) == ("sonnet", None)

    argv = claude.command("x", {}, claude.IMPLEMENTER, model=batch.model, effort=batch.effort)

    assert flag(argv, "--model") == "sonnet"
    assert "--effort" not in argv


def test_the_model_and_effort_flags_of_run_override_the_model_line(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\nModel: opus, max\n")

    world.run("run", "--model", "haiku", "--effort", "low", str(BATCH))

    calls = world.claude_calls()
    assert calls
    for call in calls:
        assert flag(call["argv"], "--model") == "haiku"
        assert flag(call["argv"], "--effort") == "low"


def test_ship_runs_its_review_on_the_model_and_effort_it_is_given(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    code = world.run(
        "ship", "10", "--title", "feat: x", "--body-file", str(body),
        "--model", "opus", "--effort", "high",
    )  # fmt: skip

    assert code == 0
    reviews = [call for call in world.claude_calls() if call["kind"] == "review"]
    assert len(reviews) == 1
    assert flag(reviews[0]["argv"], "--model") == "opus"
    assert flag(reviews[0]["argv"], "--effort") == "high"


def test_without_a_model_line_or_flags_the_command_line_is_as_before() -> None:
    batch = plan.parse_plan("Lane 1: #1\n")
    assert (batch.model, batch.effort) == (None, None)

    argv = claude.command("x", {}, claude.IMPLEMENTER, model=batch.model, effort=batch.effort)

    assert argv == [
        "claude", "-p", "x",
        "--output-format", "json",
        "--json-schema", "{}",
        "--permission-prompts", "none",
        "--settings", str(claude.SETTINGS),
        "--permission-mode", "auto",
    ]  # fmt: skip
    assert claude.command("x", {}, claude.IMPLEMENTER) == argv


@pytest.mark.parametrize("line", ["Model: opus, huge", "Model: opus, Max!", "Model: opus,"])
def test_an_unknown_effort_stops_the_batch_with_the_allowed_values(line: str) -> None:
    with pytest.raises(PlanError) as refused:
        plan.parse_plan(f"Lane 1: #1\n{line}\n")

    for effort in EFFORTS:
        assert effort in str(refused.value)


def test_the_start_comment_and_the_summary_say_the_model_and_effort(world: World) -> None:
    world.add_issue(10)
    world.add_batch(BATCH, "Lane 1: #10\nModel: opus, max\n")

    world.run("run", str(BATCH))

    comments = world.gh()["issues"][str(BATCH)]["comments"]
    started, summary = comments[0], comments[-1]
    assert "The batch started" in started
    assert "Batch summary" in summary
    for comment in (started, summary):
        assert "**Model:** opus" in comment
        assert "**Effort:** max" in comment
