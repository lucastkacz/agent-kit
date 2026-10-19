"""`make test` back under 30 seconds on an idle computer (#165, SPEC §7.3).

Most tests build a world and run the runner through its fakes, so a world's git and its fakes are
where the suite spends its time.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import World, git


def test_a_world_runs_git_from_gits_own_directory_not_through_a_wrapper(world: World) -> None:
    # macOS's /usr/bin/git looks for the developer tools' git before it runs it, on every call.
    found = shutil.which("git")
    assert found is not None
    assert Path(found).parent == Path(git(world.root, "--exec-path").strip())


def test_a_worlds_fakes_are_kept_in_pytests_cache_from_one_session_to_the_next(
    world: World, request: pytest.FixtureRequest
) -> None:
    # macOS checks a new executable on its first run, so fakes written anew each session wait.
    cache = request.config.cache
    assert cache is not None
    kept = cache.mkdir("fakes").resolve()
    for fake in (world.root / "bin").iterdir():
        assert fake.resolve().is_relative_to(kept), fake
