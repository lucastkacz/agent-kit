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

    def records(self, event: str) -> list[dict[str, object]]:
        """The events of this kind logged so far, oldest first."""
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        records: list[dict[str, object]] = []
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # A run killed while it wrote leaves its last line cut short.
            if isinstance(record, dict) and record.get("event") == event:
                records.append(record)
        return records
