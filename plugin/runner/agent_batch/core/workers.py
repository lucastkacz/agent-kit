"""How many pytest workers each lane's tests run, when many lanes share a computer (#198)."""

from __future__ import annotations

# What the Makefile reads, and its own count, which lanes this few at once keep.
WORKERS_ENV = "PYTEST_WORKERS"
MAKEFILE_WORKERS = 4
LANES_AT_FULL_SPEED = 3


def pytest_env(lanes_at_once: int, cores: int | None) -> dict[str, str]:
    """The environment that sets each lane's workers, or nothing when they run as the Makefile says.

    Past `LANES_AT_FULL_SPEED` lanes, the lanes share the cores, with at least one worker each and
    never more than the Makefile's. A computer that can't count its cores runs them as ever.
    """
    if lanes_at_once <= LANES_AT_FULL_SPEED or cores is None:
        return {}
    workers = max(1, min(MAKEFILE_WORKERS, cores // lanes_at_once))
    return {WORKERS_ENV: str(workers)}
