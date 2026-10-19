"""The check on a recorded `claude` stream that the recording's test and its own tests share."""

from __future__ import annotations

import json
from pathlib import Path

from agent_batch.core import progress


def check_recorded_stream(recording: Path) -> None:
    """Each assistant message in the recording carries its id and some tokens.

    Each `make contract` records a different number of messages, so only what each carries counts.
    """
    messages = json.loads(recording.read_text(encoding="utf-8"))
    assistants = [message for message in messages if message.get("type") == "assistant"]

    assert assistants, "the recording has no assistant message"
    for message in assistants:
        entry = progress.usage(json.dumps(message))
        assert entry is not None, f"an assistant message has no id or no usage: {message}"
        assert entry[1] > 0, f"message {entry[0]} has no tokens"
