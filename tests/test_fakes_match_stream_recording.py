"""The fake claude's stream has the shape of a real one, which `make contract` records (#107)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fake_claude

from test_fakes_match_recordings import CLAUDE_FIELDS, MISSING, kind, pluck

RECORDED = Path(__file__).parent / "contract" / "recorded" / "claude-stream.json"
# The fields the runner reads from a tool use, and from each tool's input for its short form.
TOOL_FIELDS = ("type", "id", "name", "input")
INPUT_FIELDS = {"Read": "file_path", "Edit": "file_path", "Write": "file_path", "Bash": "command"}


def recorded() -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = json.loads(RECORDED.read_text(encoding="utf-8"))
    return messages


def tool_uses(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        block
        for message in messages
        if message.get("type") == "assistant"
        for block in message["message"]["content"]
        if block.get("type") == "tool_use"
    ]


def test_the_real_stream_ends_in_its_result_after_its_tool_uses() -> None:
    messages = recorded()

    assert messages[-1]["type"] == "result"
    assert tool_uses(messages), "the recording has no tool use"
    for block in tool_uses(messages):
        field = INPUT_FIELDS.get(block["name"])
        if field is not None:
            assert isinstance(block["input"].get(field), str), f"{block['name']}: {field}"


def test_the_fakes_tool_use_message_has_the_real_ones_shape() -> None:
    real = next(
        message
        for message in recorded()
        if message.get("type") == "assistant" and tool_uses([message])
    )
    fake = fake_claude.tool_message({"name": "Read", "input": {"file_path": "/a.py"}})

    assert kind(pluck(fake, "type")) == kind(pluck(real, "type"))
    real_block, fake_block = tool_uses([real])[0], tool_uses([fake])[0]
    for field in TOOL_FIELDS:
        assert pluck(real_block, field) is not MISSING, f"the real tool use has no {field}"
        assert kind(pluck(fake_block, field)) == kind(pluck(real_block, field)), field


def test_the_fakes_result_message_has_the_real_ones_shape() -> None:
    real = recorded()[-1]
    fake = fake_claude.result_json("review", 7, {"denials": 1}, 0)

    for field in CLAUDE_FIELDS:
        assert pluck(real, field) is not MISSING, f"the real result has no {field}"
        assert kind(pluck(fake, field)) == kind(pluck(real, field)), field
