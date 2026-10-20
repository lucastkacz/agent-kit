"""run-batch creates the cloud routines through its agent, so their prompts stay out (#213)."""

from __future__ import annotations

from run_batch_skill import section, skill_text


def test_the_agent_creates_and_clears_each_routine_and_reports_only_its_id_and_time() -> None:
    send = section(skill_text(), "Send an issue to the cloud")
    for words in (
        "`agent-kit:routines` type",
        "`create`",
        "`clear_mcp_connections: true`",
    ):
        assert words in send, (words, send)
    agent = send.index("`agent-kit:routines` type")
    assert agent < send.index("`create`"), send
    assert "reports only" in send, send
    assert "routine id" in send, send
    assert "when it fires" in send, send
