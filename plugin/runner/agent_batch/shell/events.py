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
