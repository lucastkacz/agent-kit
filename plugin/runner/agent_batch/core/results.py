"""What headless Claude runs must return, and how it's read."""

from __future__ import annotations

import json
import re

from agent_batch.core.model import (
    ClaudeRun,
    Denial,
    Finding,
    FoundIssue,
    ImplementResult,
    ImplementStatus,
    IssueKind,
    ResolveResult,
    ReviewResult,
)

LIMIT = re.compile(r"\b(?:usage|rate) limit", re.IGNORECASE)

_TEXT = {"type": "string"}
FINDING_FIELDS = ("severity", "origin", "location", "problem", "suggestion")
IMPLEMENT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "status": {"enum": ["done", "blocked", "failed"]},
        "title": _TEXT,
        "pr_body": _TEXT,
        "message": _TEXT,
        "found": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"enum": ["bug", "idea", "task"]},
                    "title": _TEXT,
                    "body": _TEXT,
                },
                "required": ["kind", "title", "body"],
            },
        },
    },
    "required": ["status", "title", "pr_body", "message", "found"],
}
REVIEW_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "verdict": {"enum": ["approved", "changes"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"enum": ["high", "medium", "low"]},
                    "origin": {"enum": ["new", "earlier", "regression"]},
                    "location": _TEXT,
                    "problem": _TEXT,
                    "suggestion": _TEXT,
                },
                "required": list(FINDING_FIELDS),
            },
        },
    },
    "required": ["verdict", "findings"],
}
RESOLVE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"status": {"enum": ["resolved", "failed"]}, "message": _TEXT},
    "required": ["status", "message"],
}

_STATUSES: dict[str, ImplementStatus] = {"done": "done", "blocked": "blocked", "failed": "failed"}
_KINDS: dict[str, IssueKind] = {"bug": "bug", "idea": "idea", "task": "task"}


def ends_in_result(stdout: str) -> bool:
    """Whether what `claude -p --output-format stream-json` printed ends in its result message.

    A run that ends without it, as one that dies, says why on its standard error.
    """
    try:
        raw = json.loads(_last_line(stdout))
    except json.JSONDecodeError:
        return False
    return isinstance(raw, dict) and raw.get("type") == "result"


def _last_line(stdout: str) -> str:
    lines = stdout.strip().splitlines()
    return lines[-1] if lines else ""


def parse_run(stdout: str) -> ClaudeRun:
    """Reads the result message that ends what `claude -p --output-format stream-json` printed.

    The result carries the run's answer, its denials, its cost and its session, as the single
    answer of `--output-format json` did.
    """
    try:
        raw = json.loads(_last_line(stdout))
    except json.JSONDecodeError:
        return ClaudeRun(None, None, "the run printed something that isn't JSON")
    if not isinstance(raw, dict):
        return ClaudeRun(None, None, "the run printed JSON that isn't an object")
    result = raw.get("result")
    text = result if isinstance(result, str) else ""
    data = _object(raw.get("structured_output")) or _object_from_text(text)
    error = (text or "the run failed") if raw.get("is_error") is True else None
    if error is None and data is None:
        error = "the run returned no structured output"
    cost = raw.get("total_cost_usd")
    session = raw.get("session_id")
    return ClaudeRun(
        session_id=session if isinstance(session, str) else None,
        data=None if error else data,
        error=error,
        denials=_denials(raw.get("permission_denials")),
        cost_usd=float(cost) if isinstance(cost, int | float) else 0.0,
        limit_reached=error is not None and LIMIT.search(error) is not None,
    )


def _denials(value: object) -> tuple[Denial, ...]:
    """Every denial counts, even one whose tool or input can't be read, so none goes unreviewed."""
    if not isinstance(value, list):
        return ()
    denials: list[Denial] = []
    for item in value:
        entry = _object(item) or {}
        tool = entry.get("tool_name")
        denials.append(
            Denial(
                tool=tool if isinstance(tool, str) else "unknown tool",
                tool_input=_object(entry.get("tool_input")) or {},
            )
        )
    return tuple(denials)


def _object(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return None


def _object_from_text(text: str) -> dict[str, object] | None:
    try:
        return _object(json.loads(text))
    except json.JSONDecodeError:
        return None


def _texts(data: dict[str, object], *keys: str) -> list[str] | None:
    values = [data.get(key) for key in keys]
    return (
        [v for v in values if isinstance(v, str)]
        if all(isinstance(v, str) for v in values)
        else None
    )


def to_implement(data: dict[str, object]) -> ImplementResult | None:
    status = data.get("status")
    texts = _texts(data, "title", "pr_body", "message")
    found = _found(data.get("found"))
    if not isinstance(status, str) or status not in _STATUSES or texts is None or found is None:
        return None
    title, pr_body, message = texts
    return ImplementResult(_STATUSES[status], title, pr_body, message, found)


def _found(value: object) -> tuple[FoundIssue, ...] | None:
    if not isinstance(value, list):
        return None
    found: list[FoundIssue] = []
    for item in value:
        entry = _object(item)
        texts = _texts(entry, "kind", "title", "body") if entry is not None else None
        if texts is None or texts[0] not in _KINDS:
            return None
        found.append(FoundIssue(_KINDS[texts[0]], texts[1], texts[2]))
    return tuple(found)


def to_review(data: dict[str, object]) -> ReviewResult | None:
    verdict = data.get("verdict")
    findings = to_findings(data.get("findings"))
    if verdict not in ("approved", "changes") or findings is None:
        return None
    return ReviewResult(approved=verdict == "approved", findings=findings)


def to_findings(value: object) -> tuple[Finding, ...] | None:
    """A reviewer's findings, as it answered them or as the event log kept them."""
    if not isinstance(value, list):
        return None
    parsed: list[Finding] = []
    for item in value:
        entry = _object(item)
        texts = _texts(entry, *FINDING_FIELDS) if entry else None
        if texts is None:
            return None
        parsed.append(Finding(*texts))
    return tuple(parsed)


def to_resolve(data: dict[str, object]) -> ResolveResult | None:
    status = data.get("status")
    message = data.get("message")
    if status not in ("resolved", "failed") or not isinstance(message, str):
        return None
    return ResolveResult(resolved=status == "resolved", message=message)
