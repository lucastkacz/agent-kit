"""The PRs that `ship` and a batch open close their own issue and no other (#95, medium tests)."""

from __future__ import annotations

from batch_runs import done, pr_for
from conftest import World
from ship_branches import branch_with_work, only_pr

FIXES_ANOTHER = "Adds the feature, and fixes #74.\n"


def test_the_pr_ship_opens_quotes_the_bodys_reference_to_another_issue(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")
    body.write_text(FIXES_ANOTHER)

    assert world.run("ship", "10", "--title", "feat: add it", "--body-file", str(body)) == 0

    pr_body = only_pr(world)["body"]
    assert "fixes `#74`" in pr_body
    assert pr_body.endswith("Closes #10\n")


def test_the_pr_a_batch_opens_quotes_the_bodys_reference_to_another_issue(world: World) -> None:
    world.add_issue(10)
    world.script("implement", 10, done(pr_body=FIXES_ANOTHER))
    world.add_batch(1, "Lane 1: #10\n")

    assert world.run("run", "1") == 0

    pr_body = pr_for(world, 10)["body"]
    assert "fixes `#74`" in pr_body
    assert pr_body.endswith("Closes #10\n")
