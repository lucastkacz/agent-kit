"""What tests of `systemd-inhibit` share: a fake one that can't take its lock."""

from __future__ import annotations

from conftest import World

# What `systemd-inhibit` does without a system bus: it says why on stderr and exits at once.
FAILING_INHIBIT = """#!/bin/sh
echo "Failed to inhibit: Failed to connect to bus: No such file or directory" >&2
exit 1
"""


def failing_inhibit(world: World) -> None:
    world.replace_fake("systemd-inhibit", FAILING_INHIBIT)
