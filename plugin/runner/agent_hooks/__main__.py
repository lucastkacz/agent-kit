"""`agent-kit-hook <name>`: runs one hook, with Claude Code's event on stdin."""

import sys
from collections.abc import Callable

from agent_hooks import log_denials, protect_master, session_start

HOOKS: dict[str, Callable[[], int]] = {
    "protect-master": protect_master.main,
    "session-start": session_start.main,
    "log-denials": log_denials.main,
}

hook = HOOKS.get(sys.argv[1]) if len(sys.argv) > 1 else None
if hook is None:
    sys.stderr.write(f"usage: agent-kit-hook {{{'|'.join(HOOKS)}}}\n")
    # Exit code 2 would block the tool call, so a wrong name fails without blocking.
    sys.exit(1)
sys.exit(hook())
