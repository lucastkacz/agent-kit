"""The runner shares the pytest workers by the CPUs it may use, not all the computer has (#212).

`os.cpu_count` counts every logical CPU, even those CPU affinity or a container's cpuset keep from
the runner; `os.process_cpu_count` counts only the usable ones. The tests hand the runner its count
instead of patching `os`. `agent-batch run` runs with real git and fake `gh` and `claude`.
"""

from __future__ import annotations

import inspect
import os
import re
from pathlib import Path

import pytest

from agent_batch import cli
from conftest import World

TESTS = Path(__file__).parent
# A monkeypatch of `os.cpu_count` or `os.process_cpu_count`.
PATCHED_COUNT = re.compile(r"setattr\(\s*os\s*,\s*[\"'](?:process_)?cpu_count")


def test_the_runner_counts_only_the_cpus_it_may_use() -> None:
    cores = inspect.signature(cli.main).parameters.get("cores")

    assert cores is not None, "the runner takes no count of cores"
    assert cores.default is os.process_cpu_count, cores.default


@pytest.mark.parametrize(("cores", "workers"), [(4, "1"), (9, "2"), (64, "4")])
def test_more_than_three_lanes_share_the_cores_the_runner_is_given(
    world: World, monkeypatch: pytest.MonkeyPatch, cores: int, workers: str
) -> None:
    monkeypatch.delenv("PYTEST_WORKERS", raising=False)
    plan = ""
    for lane in range(1, 5):
        world.add_issue(10 + lane)
        plan += f"Lane {lane}: #{10 + lane}\n"
    world.add_batch(1, f"{plan}Lanes: 4\n")
    world.cores = cores

    assert world.run("run", "--max-issues", "1", "1") == 0

    assert {call["pytest_workers"] for call in world.claude_calls()} == {workers}


def test_no_test_sets_the_cores_by_patching_os() -> None:
    patched = [
        path.relative_to(TESTS).as_posix()
        for path in TESTS.rglob("*.py")
        if PATCHED_COUNT.search(path.read_text(encoding="utf-8"))
    ]

    assert patched == [], f"these tests set the cores by patching os: {patched}"
