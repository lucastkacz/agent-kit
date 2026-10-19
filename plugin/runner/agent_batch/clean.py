"""`agent-batch clean`: deletes the local branches whose PR merged (SPEC §5, step 8).

GitHub deletes a merged PR's remote branch, but the local one stays: a high-risk PR merges after
its lane ended, and a cloud issue's branch never had a lane.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from agent_batch.context import Context
from agent_batch.core import cleanup
from agent_batch.core.cleanup import Verdict
from agent_batch.core.config import LANE, LANE_FOLDERS
from agent_batch.core.model import LocalBranch, MergedPr
from agent_batch.shell.github import GitHub
from agent_batch.shell.proc import CommandError

# The merged PRs one read brings, newest first; GitHub sends them 100 to a page.
RECENT_MERGED = 200


class MergedPrs:
    """Each branch's merged PRs: the latest in one read, and older ones a branch at a time."""

    def __init__(self, gh: GitHub) -> None:
        self._gh = gh
        recent = gh.recent_merged_prs(RECENT_MERGED)
        self._complete = len(recent) < RECENT_MERGED
        self._by_branch: defaultdict[str, list[MergedPr]] = defaultdict(list)
        for pr in recent:
            self._by_branch[pr.branch].append(pr)

    def of(self, branch: str) -> list[MergedPr]:
        # A branch among the latest isn't asked about again: an older PR of a reused name can
        # only match a stale head, and missing it keeps the branch.
        if branch in self._by_branch or self._complete:
            return self._by_branch.get(branch, [])
        return self._gh.merged_prs(branch)


def clean_branches(ctx: Context) -> None:
    branches = [
        branch
        for branch in ctx.git.local_branches(ctx.repo)
        if branch.name != ctx.config.base_branch
    ]
    if not branches:
        return
    merged = MergedPrs(ctx.gh)
    for branch in branches:
        _clean(ctx, branch, merged)


def _clean(ctx: Context, branch: LocalBranch, merged: MergedPrs) -> None:
    """Deletes the branch and its worktree when its work merged; logs why when it stays."""
    try:
        verdict = _decide(ctx, branch, merged)
        if verdict.delete:
            if branch.worktree is not None:
                ctx.git.remove_clean_worktree(ctx.repo, branch.worktree)
            ctx.git.delete_branch(ctx.repo, branch.name, branch.head)
    except CommandError as error:
        verdict = Verdict(delete=False, reason=f"the cleanup failed: {error}")
    fields: dict[str, object] = {"branch": branch.name}
    if verdict.pr is not None:
        fields["pr"] = verdict.pr
    if branch.worktree is not None:
        fields["worktree"] = str(branch.worktree)
    event = "branch_deleted" if verdict.delete else "branch_kept"
    ctx.events.emit(event, **fields, reason=verdict.reason)


def _decide(ctx: Context, branch: LocalBranch, merged: MergedPrs) -> Verdict:
    changed = branch.worktree is not None and not ctx.git.is_clean(branch.worktree)
    lane = _lane(ctx, branch.worktree)
    return cleanup.decide(branch, merged.of(branch.name), lane=lane, changed=changed)


def _lane(ctx: Context, worktree: Path | None) -> str | None:
    """The name of the runner's lane worktree this is, such as `lane-1`, if it's one."""
    if worktree is None:
        return None
    state = (ctx.repo / ctx.config.state_dir).resolve()
    folder = worktree.resolve()
    in_lanes = folder.parent in {state / lanes for lanes in LANE_FOLDERS}
    return folder.name if in_lanes and folder.name.startswith(LANE) else None
