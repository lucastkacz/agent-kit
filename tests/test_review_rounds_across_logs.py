"""A branch's review rounds count across the project's logs (#74's review).

A branch can be reviewed in a batch and then finished with `agent-batch ship`; its next review
still knows it's the third, and gets the batch's findings.
"""

from __future__ import annotations

import json

from conftest import World, git

PROBLEM = "It reads the file twice."
NEW_MEDIUM = {
    "severity": "medium",
    "origin": "new",
    "location": "c.py:12",
    "problem": PROBLEM,
    "suggestion": "Read it once.",
}
BATCH_FINDING = {**NEW_MEDIUM, "severity": "high", "problem": "It crashes on an empty file."}


def test_shipping_a_branch_a_batch_reviewed_twice_makes_its_third_review(world: World) -> None:
    world.add_issue(10)
    git(world.project, "switch", "--quiet", "--create", "10-add-feature")
    (world.project / "feature.txt").write_text("work\n")
    git(world.project, "add", "-A")
    git(world.project, "commit", "--quiet", "-m", "feat: work")
    head = git(world.project, "rev-parse", "HEAD").strip()
    log = world.project / ".agent-batch" / "batch-1" / "events.jsonl"
    log.parent.mkdir(parents=True)
    reviewed = {"event": "reviewed", "branch": "10-add-feature", "head": head}
    rounds = [
        {
            **reviewed,
            "time": f"2000-01-01T10:0{n}:00+00:00",
            "round": n,
            "findings": [BATCH_FINDING],
        }
        for n in (1, 2)
    ]
    log.write_text("".join(json.dumps(record) + "\n" for record in rounds))
    world.script("review", 10, {"output": {"verdict": "changes", "findings": [NEW_MEDIUM]}})
    body = world.root / "body.md"
    body.write_text("Adds the feature.\n")

    code = world.run("ship", "10", "--title", "feat: x", "--body-file", str(body))

    review = next(c for c in world.claude_calls() if c["kind"] == "review")
    prompt = review["argv"][review["argv"].index("-p") + 1]
    assert "review 3 of this branch" in prompt
    assert BATCH_FINDING["problem"] in prompt
    assert code == 0
    assert any(PROBLEM in issue["body"] for issue in world.gh()["issues"].values())
