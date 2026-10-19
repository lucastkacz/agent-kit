"""How many pytest workers each lane gets when many lanes share a computer (#198, small tests)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import workers
from agent_batch.core.workers import MAKEFILE_WORKERS, WORKERS_ENV


@given(st.integers(min_value=4, max_value=64), st.integers(min_value=1, max_value=256))
def test_many_lanes_share_the_cores_with_one_worker_each_at_least(lanes: int, cores: int) -> None:
    workers_each = int(workers.pytest_env(lanes, cores)[WORKERS_ENV])

    assert 1 <= workers_each <= MAKEFILE_WORKERS
    assert workers_each * lanes <= max(cores, lanes)


@given(st.integers(min_value=1, max_value=3), st.one_of(st.none(), st.integers(1, 256)))
def test_few_lanes_or_uncounted_cores_leave_the_workers_to_the_makefile(
    lanes: int, cores: int | None
) -> None:
    assert workers.pytest_env(lanes, cores) == {}
    assert workers.pytest_env(lanes + 3, None) == {}
