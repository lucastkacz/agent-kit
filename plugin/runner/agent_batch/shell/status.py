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

    def __init__(self, path: Path, pid: int, spent: tuple[float, int] = (0.0, 0)) -> None:
        self.path = path
        self._pid = pid
        self._lanes: dict[int, LaneState] = {}
        self._lock = threading.Lock()
        self._failed = False
        # Set once a batch's runner opens the board: only its record shows with no lanes (#217).
        self._runner = False
        # What the ended runs cost, and their tokens: the rate that prices a running run's (#144).
        # A resumed batch starts with its earlier runs', from its event log (#156).
        self._spent_usd, self._spent_tokens = spent

    def open(self) -> None:
        """The runner starts: its batch shows with no lanes until the first one starts (#217)."""
        with self._lock:
            self._runner = True
            self._write()

    def close(self) -> None:
        """The runner ends: its batch no longer shows, even before its process exits.

        Only its own file goes: another runner may have written here since.
        """
        with self._lock:
            try:
                record = progress.parse_status(self.path.read_text(encoding="utf-8"))
                if record is not None and record[0] == self._pid:
                    self.path.unlink()
            except OSError:
                pass  # No file, or one it can't remove: a runner that's gone doesn't show anyway.

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

    def used(self, lane: int, tokens: int) -> None:
        """The lane's running run used `tokens` more, which add to its estimate."""
        self._change(lane, lambda state: self._priced(replace(state, tokens=state.tokens + tokens)))

    def spent(self, lane: int, cost_usd: float) -> None:
        """A run ended: the lane's measured cost is `cost_usd`, and its run's tokens set the rate.

        A run that ended without a cost, as one that died, or without tokens, leaves the rate as
        it was: either would skew it.
        """
        with self._lock:
            state = self._lanes.get(lane)
            if state is None:
                return
            run_usd = cost_usd - state.cost_usd
            if run_usd > 0 and state.tokens > 0:
                self._spent_usd += run_usd
                self._spent_tokens += state.tokens
            self._lanes[lane] = replace(state, cost_usd=cost_usd, tokens=0, estimate_usd=None)
            self._lanes = {key: self._priced(other) for key, other in self._lanes.items()}
            self._write()

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

    def _priced(self, state: LaneState) -> LaneState:
        if not state.tokens:
            return state
        priced = progress.estimate(state.tokens, self._spent_usd, self._spent_tokens)
        return replace(state, estimate_usd=priced)

    def _write(self) -> None:
        """Rewrites the file; one that can't be written is said once, and never ends a run.

        Tool uses come from the thread that reads a run's output: an error there would end it.
        """
        lanes = {str(lane): asdict(state) for lane, state in self._lanes.items()}
        # Named after this runner, so that another one writing here never takes it away.
        staged = self.path.with_name(f"{self.path.stem}.{self._pid}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            record = {"pid": self._pid, "runner": self._runner, "lanes": lanes}
            staged.write_text(json.dumps(record), encoding="utf-8")
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
    return [row for _, rows in _live(state_dir).values() for row in rows]


def idle(state_dir: Path) -> list[str]:
    """The batches whose runner still runs with no lane at work, as before its first one starts.

    Only a record its runner opened: a file that an older runner, or `ship`, left with no lanes
    isn't one, even when its process id runs again, or always does, where it can't be told.
    """
    return [run for run, (opened, rows) in _live(state_dir).items() if opened and not rows]


def _live(state_dir: Path) -> dict[str, tuple[bool, list[Row]]]:
    """Whether a runner opened each run's record, and its lanes, by its state's folder."""
    runs: dict[str, tuple[bool, list[Row]]] = {}
    for path in sorted(state_dir.glob(f"*/{STATUS}")):
        text = path.read_text(encoding="utf-8")
        record = progress.parse_status(text)
        if record is None or not system.is_running(record[0]):
            continue
        run = path.parent.name
        rows = [Row(run, lane, state) for lane, state in record[1]]
        runs[run] = (progress.opened_by_runner(text), rows)
    return runs
