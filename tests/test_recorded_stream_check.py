"""The recorded stream's check reads what each message carries, not how many there are (#183)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from recorded_stream import check_recorded_stream

USAGE = {"input_tokens": 2, "cache_read_input_tokens": 300, "output_tokens": 5}
RESULT = {"type": "result", "subtype": "success", "total_cost_usd": 0.01}


def assistant(identity: str | None, usage: dict[str, int] | None = USAGE) -> dict[str, Any]:
    body: dict[str, Any] = {"content": [{"type": "text", "text": "hi"}]}
    if identity is not None:
        body["id"] = identity
    if usage is not None:
        body["usage"] = usage
    return {"type": "assistant", "message": body}


def check(messages: list[dict[str, Any]], tmp_path: Path) -> None:
    recording = tmp_path / "claude-stream.json"
    recording.write_text(json.dumps(messages), encoding="utf-8")
    check_recorded_stream(recording)


def four_messages() -> list[dict[str, Any]]:
    first = assistant("msg_1")
    return [first, first, assistant("msg_2"), assistant("msg_3"), assistant("msg_4"), RESULT]


def test_a_recording_of_four_messages_each_with_its_id_and_tokens_passes(
    tmp_path: Path,
) -> None:
    check(four_messages(), tmp_path)


def test_a_recording_with_a_message_without_an_id_fails(
    tmp_path: Path,
) -> None:
    messages = [assistant("msg_1"), assistant("msg_2"), assistant("msg_3"), assistant(None), RESULT]

    with pytest.raises(AssertionError):
        check(messages, tmp_path)


def test_a_recording_with_a_message_without_tokens_fails(
    tmp_path: Path,
) -> None:
    messages = [assistant("msg_1"), assistant("msg_2"), assistant("msg_3"), RESULT]
    messages.insert(1, assistant("msg_4", usage=None))

    with pytest.raises(AssertionError):
        check(messages, tmp_path)


def test_a_recording_with_a_message_whose_tokens_are_all_zero_fails(
    tmp_path: Path,
) -> None:
    messages = [*four_messages()[:-1], assistant("msg_5", usage={"input_tokens": 0}), RESULT]

    with pytest.raises(AssertionError):
        check(messages, tmp_path)


def test_a_recording_without_an_assistant_message_fails(
    tmp_path: Path,
) -> None:
    with pytest.raises(AssertionError):
        check([RESULT], tmp_path)
