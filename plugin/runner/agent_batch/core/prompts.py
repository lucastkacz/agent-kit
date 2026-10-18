"""What the runner asks each Claude run to do."""

from __future__ import annotations

from collections.abc import Sequence

from agent_batch.core.model import Finding


def implement(number: int) -> str:
    return f"/agent-kit:implement {number}"


def review(number: int) -> str:
    return f"/agent-kit:review {number}"


def fix(number: int, findings: Sequence[Finding]) -> str:
    return (
        f"The reviewer asked for changes on #{number}. Address each finding, keep `make check` "
        "passing, commit, and answer with the same JSON as before.\n\n" + findings_list(findings)
    )


def resolve(number: int, base: str, conflicts: Sequence[str]) -> str:
    files = "\n".join(f"- `{path}`" for path in conflicts)
    return (
        f"Merging `{base}` into the branch of #{number} left conflicts in these files:\n\n"
        f"{files}\n\nResolve them keeping the intent of both sides, run `make check` until it "
        "passes, and commit the merge. Answer with `resolved`, or with `failed` and why."
    )


def findings_list(findings: Sequence[Finding]) -> str:
    return "\n".join(
        f"- **{f.severity}** `{f.location}`: {f.problem} Suggestion: {f.suggestion}"
        for f in findings
    )
