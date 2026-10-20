"""Each world copies the repos its session built once, and works on them as on its own (#165)."""

from conftest import World, git


def test_a_worlds_project_pushes_to_its_own_origin(world: World) -> None:
    (world.project / "new.txt").write_text("new\n")
    git(world.project, "add", "new.txt")
    git(world.project, "commit", "--quiet", "-m", "feat: add a file")
    git(world.project, "push", "--quiet", "origin", "HEAD:master")

    assert git(world.origin, "rev-parse", "master") == git(world.project, "rev-parse", "HEAD")


def test_a_worlds_project_starts_with_nothing_to_commit(world: World) -> None:
    assert git(world.project, "status", "--porcelain") == ""
