"""What headless Claude runs must return, and how it's read."""

from __future__ import annotations

import json
import re

from agent_batch.core.model import (
    ClaudeRun,
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
                    "location": _TEXT,
                    "problem": _TEXT,
                    "suggestion": _TEXT,
                },
                "required": ["severity", "location", "problem", "suggestion"],
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


def parse_run(stdout: str) -> ClaudeRun:
    """Reads what `claude -p --output-format json` printed."""
    try:
        raw = json.loads(stdout)
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
    denials = raw.get("permission_denials")
    cost = raw.get("total_cost_usd")
    session = raw.get("session_id")
    return ClaudeRun(
        session_id=session if isinstance(session, str) else None,
        data=None if error else data,
        error=error,
        denials=len(denials) if isinstance(denials, list) else 0,
        cost_usd=float(cost) if isinstance(cost, int | float) else 0.0,
        limit_reached=error is not None and LIMIT.search(error) is not None,
    )


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
    findings = data.get("findings")
    if verdict not in ("approved", "changes") or not isinstance(findings, list):
        return None
    parsed: list[Finding] = []
    for item in findings:
        entry = _object(item)
        texts = _texts(entry, "severity", "location", "problem", "suggestion") if entry else None
        if texts is None:
            return None
        parsed.append(Finding(*texts))
    return ReviewResult(approved=verdict == "approved", findings=tuple(parsed))


def to_resolve(data: dict[str, object]) -> ResolveResult | None:
    status = data.get("status")
    message = data.get("message")
    if status not in ("resolved", "failed") or not isinstance(message, str):
        return None
    return ResolveResult(resolved=status == "resolved", message=message)
