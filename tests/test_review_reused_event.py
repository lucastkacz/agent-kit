"""A resume that skips the review of an approved head says so in the log (#210).

The tests run `agent-batch run` twice with real git and fake `gh` and `claude` (medium tests): the
first run's push fails at GitHub after an approved review, as in batch #187.
"""

from __future__ import annotations

import pytest

from batch_runs import BATCH, events
from conftest import World
from github_server_errors import ISSUE, fail_after_the_review


def test_a_resume_that_skips_the_review_of_an_approved_head_logs_review_reused(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    fail_after_the_review(world, monkeypatch)
    [reviewed] = [e for e in events(world, BATCH) if e["event"] == "reviewed"]
    world.script("implement", ISSUE, {}, {"commits": False})

    world.run("run", str(BATCH))

    [reused] = [e for e in events(world, BATCH) if e["event"] == "review_reused"]
    assert (reused["issue"], reused["branch"], reused["head"]) == (
        ISSUE,
        reviewed["branch"],
        reviewed["head"],
    )


def test_a_resume_that_reviews_a_moved_head_logs_no_review_reused(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    fail_after_the_review(world, monkeypatch)

    world.run("run", str(BATCH))

    assert not [e for e in events(world, BATCH) if e["event"] == "review_reused"]
