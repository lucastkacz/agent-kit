"""run-batch and accept-batch call `RemoteTrigger` through a plugin agent, not a fork (#213).

Each test checks the few words that carry the behavior, so rewording the skills doesn't break it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugin"
AGENT = PLUGIN / "agents" / "routines.md"
# The `Agent` tool's type for a plugin's agent is `<plugin>:<agent>`.
AGENT_TYPE = "`agent-kit:routines`"
SMALL_MODELS = frozenset({"haiku"})


def routines_agent() -> tuple[dict[str, str], str]:
    """The agent's frontmatter fields and its body."""
    assert AGENT.is_file(), f"no agent at {AGENT}"
    text = AGENT.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{AGENT.name}: no frontmatter"
    end = text.index("\n---\n", 4)
    fields = {}
    for line in text[4:end].splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, flat(text[end + 5 :])


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def run_batch(heading: str) -> str:
    text = (PLUGIN / "skills" / "run-batch" / "SKILL.md").read_text(encoding="utf-8")
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    return flat(text[start : end if end != -1 else None])


def cloud_denials() -> str:
    text = (PLUGIN / "skills" / "accept-batch" / "SKILL.md").read_text(encoding="utf-8")
    start = text.index("- **The cloud runs' denials:**")
    end = text.find("\n- **", start + 1)
    return flat(text[start:end])


def remote_trigger_sections() -> dict[str, str]:
    return {
        "Send an issue to the cloud": run_batch("Send an issue to the cloud"),
        "Bring a cloud branch back": run_batch("Bring a cloud branch back"),
        "Resume": run_batch("Resume"),
        "The cloud runs' denials": cloud_denials(),
    }


def test_the_plugin_ships_an_agent_with_remote_trigger_read_and_grep_on_a_small_model() -> None:
    fields, _ = routines_agent()
    tools = {tool.strip() for tool in fields.get("tools", "").split(",")}
    assert tools == {"RemoteTrigger", "Read", "Grep"}, tools
    assert fields.get("model") in SMALL_MODELS, fields
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert f"`{manifest['name']}:{fields.get('name')}`" == AGENT_TYPE, fields
    assert fields.get("description"), fields


def test_the_agent_makes_only_the_calls_its_caller_names_and_reports_only_what_it_asks() -> None:
    _, body = routines_agent()
    assert "only the calls your caller names" in body, body
    assert "report only what your caller asks" in body, body
    assert "`Read`" in body, body


def test_each_remote_trigger_section_hands_its_calls_to_the_agent_in_the_foreground() -> None:
    for heading, text in remote_trigger_sections().items():
        assert AGENT_TYPE in text, (heading, text)
        assert "in the foreground" in text, (heading, text)


def test_each_remote_trigger_section_says_why_the_agent_runs_in_the_foreground() -> None:
    for heading, text in remote_trigger_sections().items():
        assert "in the background" in text, (heading, text)
        why = text[text.index("in the background") :]
        assert "doesn't get `RemoteTrigger`" in why, (heading, text)


def test_only_the_create_fallback_still_forks_the_session() -> None:
    sections = remote_trigger_sections()
    for heading in ("Bring a cloud branch back", "Resume", "The cloud runs' denials"):
        assert "fork" not in sections[heading], (heading, sections[heading])


def test_run_batch_writes_each_filled_prompt_to_a_file_outside_the_repository_for_the_agent() -> (
    None
):
    send = run_batch("Send an issue to the cloud")
    assert "file outside the repository" in send, send
    assert "the agent reads" in send, send


def test_the_agent_greps_a_large_saved_answer_instead_of_reading_it_whole() -> None:
    _, body = routines_agent()
    assert "saved to a file" in body, body
    assert "`Grep`" in body, body
    assert "never read it whole" in body, body
    resume = run_batch("Resume")
    assert "`list`" in resume, resume
    assert "greps" in resume, resume


def test_run_batch_falls_back_to_the_fork_when_the_agents_create_fails_and_tells_the_owner() -> (
    None
):
    send = run_batch("Send an issue to the cloud")
    assert "Until a routine has been created through the agent" in send, send
    fallback = send[send.index("Until a routine has been created through the agent") :]
    assert "`create` fails" in fallback, fallback
    assert "fork of the session" in fallback, fallback
    assert "`fork` type" in fallback, fallback
    assert "tell the owner" in fallback, fallback
