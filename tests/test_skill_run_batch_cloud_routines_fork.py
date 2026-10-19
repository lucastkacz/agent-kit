"""run-batch creates the cloud routines through a fork, so their prompts stay out (#112)."""

from __future__ import annotations

from test_skill_run_batch_cloud_dispatch import section, skill_text


def test_a_fork_creates_and_clears_each_routine_and_reports_only_its_id_and_time() -> None:
    send = section(skill_text(), "Send an issue to the cloud")
    for words in (
        "fork of the session",
        "`fork` type",
        "`create`",
        "`clear_mcp_connections: true`",
    ):
        assert words in send, (words, send)
    fork = send.index("fork of the session")
    assert fork < send.index("`create`"), send
    assert "reports only" in send, send
    assert "routine id" in send, send
    assert "when it fires" in send, send
