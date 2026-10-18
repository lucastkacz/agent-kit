"""The git operations a batch needs: a worktree per lane and a branch per issue."""

from __future__ import annotations

from pathlib import Path

from agent_batch.core.config import Config
from agent_batch.shell import proc
from agent_batch.shell.proc import CommandError


class Git:
    def __init__(self, config: Config) -> None:
        self._remote = config.remote
        self._upstream = config.upstream

    def _git(self, cwd: Path, *args: str) -> str:
        return proc.must(["git", *args], cwd)

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

    def add_lane_worktree(self, repo: Path, path: Path) -> None:
        self._git(repo, "fetch", "--quiet", self._remote)
        self.remove_worktree(repo, path)
        self._git(repo, "worktree", "prune")
        self._git(repo, "worktree", "add", "--quiet", "--detach", str(path), self._upstream)

    def remove_worktree(self, repo: Path, path: Path) -> None:
        if path.exists():
            self._git(repo, "worktree", "remove", "--force", str(path))

    def start_branch(self, worktree: Path, branch: str) -> None:
        """Switches to the issue's branch, picking up earlier work on it if there is some."""
        self._git(worktree, "fetch", "--quiet", self._remote)
        if self._has_ref(worktree, f"refs/heads/{branch}"):
            self._git(worktree, "switch", "--quiet", branch)
        elif self._has_ref(worktree, f"refs/remotes/{self._remote}/{branch}"):
            self._git(worktree, "switch", "--quiet", "--track", f"{self._remote}/{branch}")
        else:
            self._git(worktree, "switch", "--quiet", "--create", branch, self._upstream)

    def _has_ref(self, cwd: Path, ref: str) -> bool:
        return proc.run(["git", "rev-parse", "--verify", "--quiet", ref], cwd).ok

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
        result = proc.run(["git", "show", f"{self._upstream}:{path}"], worktree)
        return result.out if result.ok else None

    def push(self, worktree: Path, branch: str) -> None:
        self._git(worktree, "push", "--quiet", "--set-upstream", self._remote, branch)

    def merge_upstream(self, worktree: Path) -> list[str]:
        """Merges the base branch in; returns the files left in conflict."""
        self._git(worktree, "fetch", "--quiet", self._remote)
        result = proc.run(["git", "merge", "--no-edit", self._upstream], worktree)
        if result.ok:
            return []
        conflicts = self._lines(worktree, "diff", "--name-only", "--diff-filter=U")
        if not conflicts:
            raise CommandError(f"merging {self._upstream} failed: {result.err.strip()}")
        return conflicts

    def finish_branch(self, worktree: Path, branch: str) -> None:
        """Leaves the merged branch, so the lane's next issue starts from the latest base."""
        self._git(worktree, "fetch", "--quiet", self._remote)
        self._git(worktree, "switch", "--quiet", "--detach", self._upstream)
        self._git(worktree, "branch", "--quiet", "-D", branch)
