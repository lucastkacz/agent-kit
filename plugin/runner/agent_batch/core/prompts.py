"""What the runner asks each Claude run to do."""

from __future__ import annotations

from collections.abc import Sequence

from agent_batch.core.model import Finding
from agent_batch.core.rounds import Round, filed


def implement(number: int) -> str:
    return f"/agent-kit:implement {number}"


def review(number: int, earlier: Sequence[Round] = ()) -> str:
    """The review skill, and on a re-review what the earlier rounds of the branch found."""
    command = f"/agent-kit:review {number}"
    if not earlier:
        return command
    rounds = "\n\n".join(_round(each) for each in earlier)
    return (
        f"{command}\n\nThis is review {len(earlier) + 1} of this branch. The earlier rounds' "
        f"findings, under the commit each review read:\n\n{rounds}"
    )


def _round(round_: Round) -> str:
    heading = f"Review {round_.number}, of `{round_.head}`:"
    if not round_.findings:
        return f"{heading} no findings."
    return "\n".join([heading, *(_earlier(each, round_.number) for each in round_.findings)])


def _earlier(finding: Finding, number: int) -> str:
    line = (
        f"- **{finding.severity}** ({finding.origin}) `{finding.location}`: {finding.problem} "
        f"Suggestion: {finding.suggestion}"
    )
    if filed(finding, number):
        line += " Filed as an issue: it's not this branch's work."
    return line


def fix(number: int, findings: Sequence[Finding]) -> str:
    # The next review reads only `git log --oneline`, so an answer's subject names the location.
    return (
        f"The reviewer asked for changes on #{number}. Fix or answer each finding, keep "
        "`make check` passing, commit, and answer with the same JSON as before.\n\n"
        "Fix every finding you agree with. Answer one only when you're sure it's wrong, or when "
        "it asks for work outside the issue. An answer is a commit whose subject names the "
        "finding's location and whose body says why it stays as it is (`git commit "
        "--allow-empty` when nothing else changes), or a code comment where the finding points.\n"
        "Always fix a finding about `make check` failing, missing or changed acceptance tests, "
        "or an unmet criterion.\n\n" + findings_list(findings)
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
