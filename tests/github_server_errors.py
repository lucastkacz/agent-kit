"""What tests of GitHub's server errors share: the errors GitHub answers, and the issue's end."""

from __future__ import annotations

from typing import Any

from batch_runs import BATCH, events
from conftest import World

ISSUE = 10
PUSH_500 = "`git push --quiet` failed: remote: Internal Server Error"
PR_GRAPHQL = (
    "`gh pr create` failed: GraphQL: Something went wrong while executing your query. This may "
    "be the result of a timeout, or it could be a GitHub bug. Please include "
    "`E322:12220F:324587:4ED219:6AD64F5E` when reporting this issue."
)


def finished(world: World) -> dict[str, Any]:
    return next(
        e for e in events(world, BATCH) if e["event"] == "issue_finished" and e["issue"] == ISSUE
    )
