"""`ship` keeps the PR in step with its review and its latest title and body (#75, medium tests)."""

from __future__ import annotations

import pytest

from batch_runs import pr_for
from conftest import World
from ship_branches import branch_with_work, only_pr

HEADING = "## Review findings"
FINDINGS = [
    {
        "severity": "low",
        "origin": "new",
        "location": "a.py:3",
        "problem": "Unclear name.",
        "suggestion": "Rename.",
    },
    {
        "severity": "medium",
        "origin": "new",
        "location": "b.py:9",
        "problem": "No test.",
        "suggestion": "Add one.",
    },
]
APPROVED_WITH_FINDINGS = {"output": {"verdict": "approved", "findings": FINDINGS}}


def findings_section(body: str) -> str:
    assert HEADING in body, body
    return body.split(HEADING, 1)[1].split("\n## ", 1)[0]


def assert_each_finding_has_its_severity(body: str) -> None:
    lines = findings_section(body).splitlines()
    for finding in FINDINGS:
        assert any(finding["severity"] in line and finding["problem"] in line for line in lines), (
            finding
        )


def test_an_approved_reviews_findings_go_into_the_pr_body_with_their_severity(
    world: World,
) -> None:
    world.add_issue(10)
    world.script("review", 10, APPROVED_WITH_FINDINGS)
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "feat: add it", "--body-file", str(body)) == 0

    assert_each_finding_has_its_severity(only_pr(world)["body"])


def test_an_approved_review_without_findings_leaves_the_heading_out(world: World) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "feat: add it", "--body-file", str(body)) == 0

    assert "Review findings" not in only_pr(world)["body"]


def test_the_batch_puts_an_approved_reviews_findings_in_the_pr_body(world: World) -> None:
    world.add_issue(10)
    # The second review is the one after the low pass, whose findings go to the PR (#252).
    world.script("review", 10, APPROVED_WITH_FINDINGS, APPROVED_WITH_FINDINGS)
    world.add_batch(1, "Lane 1: #10\n")

    assert world.run("run", "1") == 0

    assert_each_finding_has_its_severity(pr_for(world, 10)["body"])


def test_shipping_a_branch_whose_pr_is_open_updates_its_title_and_body(world: World) -> None:
    world.add_issue(10)
    first = branch_with_work(world, "10-add-feature")
    assert world.run("ship", "10", "--title", "feat: first try", "--body-file", str(first)) == 0
    second = world.root / "second.md"
    second.write_text("Adds the feature, done better.\n")

    assert world.run("ship", "10", "--title", "feat: second try", "--body-file", str(second)) == 0

    pr = only_pr(world)
    assert pr["title"] == "feat: second try"
    assert "Adds the feature, done better." in pr["body"]
    assert "Adds the feature.\n" not in pr["body"]
    assert "Closes #10" in pr["body"]


def test_ship_says_nothing_about_a_title_it_used(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.add_issue(10)
    body = branch_with_work(world, "10-add-feature")

    assert world.run("ship", "10", "--title", "feat: add it", "--body-file", str(body)) == 0

    assert "title" not in capsys.readouterr().out.lower()
