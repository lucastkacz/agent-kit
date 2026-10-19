"""Which local branches may go: only those whose work merged on GitHub (SPEC §5, step 8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from agent_batch.core.model import LocalBranch, MergedPr

SHORT_SHA = 7


@dataclass(frozen=True)
class Verdict:
    delete: bool
    reason: str
    pr: int | None = None


def decide(
    branch: LocalBranch, merged: Sequence[MergedPr], *, lane: str | None, changed: bool
) -> Verdict:
    """Deletes a branch only when a PR merged at its head and its worktree has no changes.

    The head is compared, not the commits: after a squash merge, none of the branch's commits
    is on the base branch, so git can't tell a merged branch from one with work left. `lane`
    names the runner's lane worktree the branch is checked out in: a running lane keeps its
    merged branch until its next poll, then deletes it itself.
    """
    if not merged:
        return Verdict(delete=False, reason="it has no merged PR")
    pr = next((pr for pr in merged if pr.head == branch.head), None)
    if pr is None:
        heads = ", ".join(f"#{pr.number} merged at {pr.head[:SHORT_SHA]}" for pr in merged)
        reason = f"its head {branch.head[:SHORT_SHA]} has work no PR merged ({heads})"
        return Verdict(delete=False, reason=reason)
    if branch.main_folder:
        reason = f"PR #{pr.number} merged, but the branch is checked out in the main folder"
        return Verdict(delete=False, reason=reason, pr=pr.number)
    if lane is not None:
        reason = (
            f"PR #{pr.number} merged, but it's checked out in the runner's {lane} worktree, "
            "which its lane cleans up"
        )
        return Verdict(delete=False, reason=reason, pr=pr.number)
    if changed:
        reason = f"PR #{pr.number} merged, but its worktree {branch.worktree} has changes"
        return Verdict(delete=False, reason=reason, pr=pr.number)
    return Verdict(delete=True, reason=f"PR #{pr.number} merged at its head", pr=pr.number)
