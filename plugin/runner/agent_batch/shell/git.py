"""The git operations a batch needs: a worktree per lane and a branch per issue."""

from __future__ import annotations

import threading
from pathlib import Path

from agent_batch.core.config import Config
from agent_batch.core.model import LocalBranch
from agent_batch.shell import proc
from agent_batch.shell.proc import CommandError

# The lanes' worktrees share one repository, and git fails instead of waiting when another
# command holds one of its lock files (the config, a remote ref), so the runner's git commands
# take turns.
_ONE_AT_A_TIME = threading.Lock()
HEADS = "refs/heads/"


class Git:
    def __init__(self, config: Config) -> None:
        self._remote = config.remote
        self._upstream = config.upstream

    def _run(self, cwd: Path, *args: str) -> proc.Result:
        with _ONE_AT_A_TIME:
            return proc.run(["git", *args], cwd)

    def _git(self, cwd: Path, *args: str) -> str:
        return proc.output(["git", *args], self._run(cwd, *args))

    def _lines(self, cwd: Path, *args: str) -> list[str]:
        return [line for line in self._git(cwd, *args).splitlines() if line]

    def main_root(self, cwd: Path) -> Path:
        """The main checkout's folder, also when `cwd` is inside a worktree."""
        common = self._git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
        return Path(common.strip()).parent

    def toplevel(self, cwd: Path) -> Path:
        return Path(self._git(cwd, "rev-parse", "--show-toplevel").strip())

    def current_branch(self, worktree: Path) -> str:
        return self._git(worktree, "branch", "--show-current").strip()

    def fetch(self, worktree: Path) -> None:
        self._git(worktree, "fetch", "--quiet", self._remote)

    def add_lane_worktree(self, repo: Path, path: Path) -> None:
        self._git(repo, "fetch", "--quiet", self._remote)
        self.remove_worktree(repo, path)
        self._git(repo, "worktree", "prune")
        self._git(repo, "worktree", "add", "--quiet", "--detach", str(path), self._upstream)

    def remove_worktree(self, repo: Path, path: Path) -> None:
        if path.exists():
            self._git(repo, "worktree", "remove", "--force", str(path))

    def start_branch(self, worktree: Path, branch: str) -> None:
        """Switches to the issue's branch, picking up earlier work on it if there is some.

        Branches don't track the remote: that would write the shared config for nothing, since
        the runner pushes by name and never pulls.
        """
        self._git(worktree, "fetch", "--quiet", self._remote)
        remote_branch = f"{self._remote}/{branch}"
        if self._has_ref(worktree, f"refs/heads/{branch}"):
            self._git(worktree, "switch", "--quiet", branch)
        elif self._has_ref(worktree, f"refs/remotes/{remote_branch}"):
            self._git(
                worktree, "switch", "--quiet", "--no-track", "--create", branch, remote_branch
            )
        else:
            self._git(
                worktree, "switch", "--quiet", "--no-track", "--create", branch, self._upstream
            )

    def _has_ref(self, cwd: Path, ref: str) -> bool:
        return self._run(cwd, "rev-parse", "--verify", "--quiet", ref).ok

    def is_clean(self, worktree: Path) -> bool:
        return not self._git(worktree, "status", "--porcelain").strip()

    def commits_ahead(self, worktree: Path) -> int:
        return int(self._git(worktree, "rev-list", "--count", f"{self._upstream}..HEAD").strip())

    def changed_files(self, worktree: Path) -> list[str]:
        return self._lines(worktree, "diff", "--name-only", f"{self._upstream}...HEAD")

    def head(self, worktree: Path) -> str:
        return self._git(worktree, "rev-parse", "HEAD").strip()

    def base_file(self, worktree: Path, path: str) -> str | None:
        """A file as it is on the base branch, which the batch's agents can't change."""
        result = self._run(worktree, "show", f"{self._upstream}:{path}")
        return result.out if result.ok else None

    def push(self, worktree: Path, branch: str) -> None:
        self._git(worktree, "push", "--quiet", self._remote, branch)

    def merge_upstream(self, worktree: Path) -> list[str]:
        """Merges the base branch in; returns the files left in conflict."""
        self._git(worktree, "fetch", "--quiet", self._remote)
        result = self._run(worktree, "merge", "--no-edit", self._upstream)
        if result.ok:
            return []
        conflicts = self._lines(worktree, "diff", "--name-only", "--diff-filter=U")
        if not conflicts:
            raise CommandError(f"merging {self._upstream} failed: {result.err.strip()}")
        return conflicts

    def local_branches(self, repo: Path) -> list[LocalBranch]:
        """The repository's branches, each with the worktree it's checked out in, if any.

        Worktrees whose folder is gone are pruned first, since git counts their branch as
        checked out there and refuses to delete it.
        """
        self._git(repo, "worktree", "prune")
        checked_out = _checked_out(self._git(repo, "worktree", "list", "--porcelain"))
        branches = []
        for line in self._lines(repo, "for-each-ref", "--format=%(objectname) %(refname)", HEADS):
            head, ref = line.split(" ", 1)
            name = ref.removeprefix(HEADS)
            worktree, main_folder = checked_out.get(name, (None, False))
            branches.append(LocalBranch(name, head, worktree, main_folder))
        return branches

    def remove_clean_worktree(self, repo: Path, path: Path) -> None:
        """Removes a worktree; git refuses one with changes or a lock, so no work is lost."""
        self._git(repo, "worktree", "remove", str(path))

    def delete_branch(self, repo: Path, branch: str) -> None:
        # `-D`: after a squash merge, `-d` refuses the branch as unmerged.
        self._git(repo, "branch", "--quiet", "-D", branch)

    def finish_branch(self, worktree: Path, branch: str) -> None:
        """Leaves the merged branch, so the lane's next issue starts from the latest base.

        The branch goes before the fetch, so a lost connection doesn't leave it behind in the
        shared repository (#34).
        """
        self._git(worktree, "switch", "--quiet", "--detach", self._upstream)
        self._git(worktree, "branch", "--quiet", "-D", branch)
        self._git(worktree, "fetch", "--quiet", self._remote)
        self._git(worktree, "switch", "--quiet", "--detach", self._upstream)


def _checked_out(porcelain: str) -> dict[str, tuple[Path, bool]]:
    """Each checked-out branch's worktree, and whether it's the main folder, listed first."""
    found: dict[str, tuple[Path, bool]] = {}
    for index, block in enumerate(porcelain.strip().split("\n\n")):
        fields = {
            key: value for key, _, value in (line.partition(" ") for line in block.splitlines())
        }
        branch = fields.get("branch", "")
        if branch.startswith(HEADS):
            found[branch.removeprefix(HEADS)] = (Path(fields["worktree"]), index == 0)
    return found
