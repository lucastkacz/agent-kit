"""The environment the runner hands to Claude runs (SPEC §11.1)."""

from __future__ import annotations

from collections.abc import Mapping

# With an API key in the environment, a headless run bills the API instead of the subscription.
API_KEYS = frozenset({"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"})
# When the runner is started from a Claude Code session, these mark the runs as that session's
# children, which changes how they start.
SESSION_MARKERS = frozenset({"CLAUDECODE"})
SESSION_PREFIX = "CLAUDE_CODE_"
# Unlike the session markers, this one is how a subscription can sign in headless runs.
KEPT = frozenset({"CLAUDE_CODE_OAUTH_TOKEN"})
# The main checkout's virtual environment: in a lane worktree, uv warns that it doesn't match the
# worktree's own `.venv` on every command.
MAIN_CHECKOUT = frozenset({"VIRTUAL_ENV"})


def clean_env(env: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in env.items()
        if key not in API_KEYS
        and key not in SESSION_MARKERS
        and key not in MAIN_CHECKOUT
        and (not key.startswith(SESSION_PREFIX) or key in KEPT)
    }
