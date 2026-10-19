"""`agent-batch clean`: deletes the local branches whose PR merged (SPEC §5, step 8).

GitHub deletes a merged PR's remote branch, but the local one stays: a high-risk PR merges after
its lane ended, and a cloud issue's branch never had a lane.
"""

from __future__ import annotations

from agent_batch.context import Context
from agent_batch.core import cleanup
from agent_batch.core.cleanup import Verdict
from agent_batch.core.model import LocalBranch
from agent_batch.shell.proc import CommandError


def clean_branches(ctx: Context) -> None:
    for branch in ctx.git.local_branches(ctx.repo):
        if branch.name != ctx.config.base_branch:
            _clean(ctx, branch)


def _clean(ctx: Context, branch: LocalBranch) -> None:
    """Deletes the branch and its worktree when its work merged; logs why when it stays."""
    try:
        verdict = _decide(ctx, branch)
        if verdict.delete:
            if branch.worktree is not None:
                ctx.git.remove_clean_worktree(ctx.repo, branch.worktree)
            ctx.git.delete_branch(ctx.repo, branch.name)
    except CommandError as error:
        verdict = Verdict(delete=False, reason=f"the cleanup failed: {error}")
    fields: dict[str, object] = {"branch": branch.name}
    if verdict.pr is not None:
        fields["pr"] = verdict.pr
    if branch.worktree is not None:
        fields["worktree"] = str(branch.worktree)
    event = "branch_deleted" if verdict.delete else "branch_kept"
    ctx.events.emit(event, **fields, reason=verdict.reason)


def _decide(ctx: Context, branch: LocalBranch) -> Verdict:
    merged = ctx.gh.merged_prs(branch.name)
    changed = branch.worktree is not None and not ctx.git.is_clean(branch.worktree)
    return cleanup.decide(branch, merged, changed=changed)
