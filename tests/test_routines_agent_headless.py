"""The batch skills run the routines agent as a headless session, not through the Agent tool (#235).

In an interactive session the `Agent` tool starts the agent in the background, where it doesn't
get `RemoteTrigger`. A headless `claude -p --agent agent-kit:routines` runs as the agent itself.
Each test checks the few words that carry the behavior, so rewording the skills doesn't break it.
"""

from __future__ import annotations

import re
from pathlib import Path

import accept_batch_skill
from run_batch_skill import section, skill_text

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0001-a-plugin-agent-for-the-cloud-routines.md"
AGENT = ROOT / "plugin" / "agents" / "routines.md"
HEADLESS = "`claude -p --agent agent-kit:routines"
AGENT_TOOL = "`Agent` tool's `agent-kit:routines` type"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def run_batch(heading: str) -> str:
    return flat(section(skill_text(), heading))


def cloud_watch() -> str:
    watch = run_batch("Watch")
    start = watch.index("- The cloud:")
    return watch[start : watch.index(" - ", start + 1)]


def cloud_denials() -> str:
    # accept_batch_skill.section lowercases its text, and these checks name tools by their case.
    text = accept_batch_skill.text()
    start = text.index("- **The cloud runs' denials:**")
    return flat(text[start : text.index("\n- **", start + 1)])


def remote_trigger_sections() -> dict[str, str]:
    return {
        "Send an issue to the cloud": run_batch("Send an issue to the cloud"),
        "Bring a cloud branch back": run_batch("Bring a cloud branch back"),
        "Resume": run_batch("Resume"),
        "Watch": cloud_watch(),
        "The cloud runs' denials": cloud_denials(),
    }


def test_run_batch_and_accept_batch_give_the_headless_command_with_the_agents_tools() -> None:
    for text in (run_batch("Send an issue to the cloud"), cloud_denials()):
        assert HEADLESS in text, text
        assert '--allowedTools "RemoteTrigger,Read,Grep"' in text, text
        assert "project's main folder" in text, text


def test_each_remote_trigger_section_runs_the_agent_headless_never_through_the_agent_tool() -> None:
    for heading, text in remote_trigger_sections().items():
        assert "headless" in text, (heading, text)
        assert AGENT_TOOL not in text, (heading, text)
        assert "in the foreground" not in text, (heading, text)


def test_the_skills_say_why_the_agent_tool_wont_do() -> None:
    for text in (run_batch("Send an issue to the cloud"), cloud_denials()):
        assert "interactive session" in text, text
        why = text[text.index("interactive session") :]
        assert "in the background" in why, text
        assert "doesn't get `RemoteTrigger`" in why, text
        assert "#235" in why, text


def test_watch_reads_the_routines_runs_through_the_agent_not_in_the_control_tower() -> None:
    watch = cloud_watch()
    assert "`list_runs`" in watch, watch
    assert "routines agent" in watch, watch
    assert "`RemoteTrigger`'s `list_runs`" not in watch, watch
    status = run_batch("Watch")
    asked = status[status.index("When the owner asks how the batch is going") :]
    assert "routines agent" in asked, asked


def test_send_has_no_fork_fallback_and_tells_the_owner_of_a_failed_call() -> None:
    send = run_batch("Send an issue to the cloud")
    assert "fork" not in send, send
    assert "hasn't been tried yet" not in send, send
    failed = send[send.index("call that failed") :]
    assert "don't send that issue" in failed, failed
    assert "tell the owner" in failed, failed


def test_adr_0001_is_accepted_and_records_what_works_in_an_interactive_session() -> None:
    text = ADR.read_text(encoding="utf-8")
    status = re.search(r"^- \*\*Status:\*\* (.*)$", text, re.MULTILINE)
    assert status, text[:300]
    assert status.group(1).startswith("accepted"), status.group(1)
    body = flat(text)
    for words in (
        "interactive session",
        "2.1.304",
        "in the background",
        HEADLESS,
        "`CLAUDE_CODE_FORK_SUBAGENT=0`",
        "`create`",
        "`clear_mcp_connections: true`",
    ):
        assert words in body, words


def test_the_agents_description_names_the_headless_session() -> None:
    text = AGENT.read_text(encoding="utf-8")
    description = re.search(r"^description: (.*)$", text, re.MULTILINE)
    assert description, text[:300]
    assert "claude -p --agent agent-kit:routines" in description.group(1), description.group(1)
    assert "in the foreground" not in description.group(1), description.group(1)
