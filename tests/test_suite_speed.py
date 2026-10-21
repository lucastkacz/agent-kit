"""`make test` stays under 45 seconds (SPEC §7.3).

macOS checks an executable the first time it runs, which takes about half a second; a world that
wrote its fakes anew waited for that check on each of them, in every test.
"""

from conftest import World

FAKES = ("gh", "claude", "caffeinate", "pmset", "systemd-inhibit", "tail")


def test_a_worlds_fakes_are_symlinks_to_executables_that_every_world_shares(world: World) -> None:
    for name in FAKES:
        fake = world.root / "bin" / name
        assert fake.is_symlink(), f"{name} was written anew for this world"
