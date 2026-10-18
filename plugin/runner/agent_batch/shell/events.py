"""The batch's event log: JSON lines for the control tower, plain lines for whoever watches."""

from __future__ import annotations

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path


class EventLog:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()

    def emit(self, event: str, **fields: object) -> None:
        record = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "event": event, **fields}
        details = " ".join(f"{key}={value}" for key, value in fields.items())
        with self._lock:
            with self.path.open("a", encoding="utf-8") as log:
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
            sys.stdout.write(f"{record['time']} {event} {details}".rstrip() + "\n")
            sys.stdout.flush()

    def project_records(self, event: str) -> list[dict[str, object]]:
        """The events of this kind in every log of the project, this one's included, oldest first.

        A branch can be reviewed in one batch, then in another or by `agent-batch ship` (SPEC §5).
        """
        logs = sorted(self.path.parent.parent.glob(f"*/{self.path.name}"))
        with self._lock:
            found = [record for log in logs for record in _read(log, event)]
        return sorted(found, key=lambda record: str(record.get("time", "")))


def _read(log: Path, event: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # A run killed while it wrote leaves its last line cut short.
        if isinstance(record, dict) and record.get("event") == event:
            records.append(record)
    return records
