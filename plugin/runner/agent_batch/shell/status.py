"""Each lane's live state, in a file of its own next to the event log (#107).

The event log keeps a line per step, for the control tower and the acceptance. A line per tool use
would flood it, so the live state goes to `status.json`, rewritten whole on each change.
"""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path

from agent_batch.core import progress
from agent_batch.core.progress import LaneState, Row
from agent_batch.shell import system

STATUS = "status.json"


class StatusBoard:
    """The lanes of one batch, or the lane 0 of one `agent-batch ship`, and their runner's id."""

    def __init__(self, path: Path, pid: int) -> None:
        self.path = path
        self._pid = pid
        self._lanes: dict[int, LaneState] = {}
        self._lock = threading.Lock()
        self._failed = False

    def start(self, lane: int, state: LaneState) -> None:
        """The lane starts an issue; until the next one, its row shows this one."""
        with self._lock:
            self._lanes[lane] = state
            self._write()

    def step(self, lane: int, step: str, review_round: int | None = None) -> None:
        def change(state: LaneState) -> LaneState:
            if review_round is None:
                return replace(state, step=step)
            return replace(state, step=step, round=review_round)

        self._change(lane, change)

    def act(self, lane: int, action: str, when: float) -> None:
        self._change(lane, lambda state: replace(state, action=action, action_time=when))

    def spent(self, lane: int, cost_usd: float) -> None:
        self._change(lane, lambda state: replace(state, cost_usd=cost_usd))

    def drop(self, lane: int) -> None:
        """The lane ended: no more row for it."""
        with self._lock:
            if self._lanes.pop(lane, None) is not None:
                self._write()

    def _change(self, lane: int, change: Callable[[LaneState], LaneState]) -> None:
        with self._lock:
            state = self._lanes.get(lane)
            if state is not None:
                self._lanes[lane] = change(state)
                self._write()

    def _write(self) -> None:
        """Rewrites the file; one that can't be written is said once, and never ends a run.

        Tool uses come from the thread that reads a run's output: an error there would end it.
        """
        lanes = {str(lane): asdict(state) for lane, state in self._lanes.items()}
        # Named after this runner, so that another one writing here never takes it away.
        staged = self.path.with_name(f"{self.path.stem}.{self._pid}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(json.dumps({"pid": self._pid, "lanes": lanes}), encoding="utf-8")
            # A reader never sees the file half written.
            staged.replace(self.path)
        except OSError as error:
            if not self._failed:
                self._failed = True
                sys.stderr.write(
                    f"agent-batch: couldn't write the lanes' live state to {self.path}, so "
                    f"`agent-batch status` won't show it: {error}\n"
                )


def running(state_dir: Path) -> list[Row]:
    """The lanes of each batch and `agent-batch ship` whose runner still runs."""
    rows: list[Row] = []
    for path in sorted(state_dir.glob(f"*/{STATUS}")):
        record = progress.parse_status(path.read_text(encoding="utf-8"))
        if record is None or not system.is_running(record[0]):
            continue
        rows += [Row(path.parent.name, lane, state) for lane, state in record[1]]
    return rows
