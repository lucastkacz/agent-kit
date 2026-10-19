"""The denials that the PermissionDenied hook logged for a run (SPEC §10.1, #147).

Auto mode's denials of a lane reach only `.agent-batch/denials.jsonl`, not the run's answer, while
a protect-master block can reach both: each one counts once.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from agent_batch.core.model import Denial

LOG = "denials.jsonl"
# The hook keeps a short text of a call's input, by these keys in order (agent_hooks.log_denials).
INPUT_KEYS = ("command", "file_path", "url", "pattern")
MAX_INPUT = 300
# A logged denial's input is that text, not the call's whole input.
LOGGED_INPUT = "input"


def summary(tool_input: dict[str, object]) -> str:
    """The text the hook logs for a call's input."""
    for key in INPUT_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str):
            return value[:MAX_INPUT]
    return json.dumps(tool_input, ensure_ascii=False)[:MAX_INPUT]


def logged(text: str, session: str) -> list[Denial]:
    """The session's entries among the log's lines, oldest first."""
    found: list[Denial] = []
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # Another session may be writing its line as this one reads.
        if isinstance(entry, dict) and entry.get("session") == session:
            tool, shown = entry.get("tool"), entry.get("input")
            found.append(
                Denial(
                    tool=tool if isinstance(tool, str) else "unknown tool",
                    tool_input={LOGGED_INPUT: shown if isinstance(shown, str) else ""},
                    session=session,
                )
            )
    return found


def combined(
    answer: Sequence[Denial], entries: Sequence[Denial], session: str
) -> tuple[Denial, ...]:
    """The answer's denials, then each logged one that isn't among them, all of that session.

    A logged entry matches an answer's denial of the same tool and input; each matches once, so a
    command denied twice and logged twice still counts twice.
    """
    unmatched = Counter((denial.tool, summary(denial.tool_input)) for denial in answer)
    extra: list[Denial] = []
    for entry in entries:
        # The hook logs "" for an input that isn't an object, which the answer reads as {}.
        shown = str(entry.tool_input.get(LOGGED_INPUT, "")) or summary({})
        key = (entry.tool, shown)
        if unmatched[key] > 0:
            unmatched[key] -= 1
        else:
            extra.append(entry)
    return (*(replace(denial, session=session) for denial in answer), *extra)
