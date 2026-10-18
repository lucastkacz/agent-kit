"""The batch's summary and numbers (SPEC §16.2)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from agent_batch.core.model import IssueReport, Outcome

SECONDS_PER_MINUTE = 60
NEEDS_OWNER = (Outcome.WAITING_OWNER, Outcome.BLOCKED, Outcome.FAILED)


def render(reports: Sequence[IssueReport], seconds: float) -> str:
    ordered = sorted(reports, key=lambda report: report.number)
    counts = Counter(report.outcome for report in reports)
    lines = [
        "## Batch summary",
        "",
        "| Issue | Outcome | PR | Review rounds | Denials | Minutes |",
        "|---|---|---|---|---|---|",
        *(_row(report) for report in ordered),
        "",
        "**Outcomes:** " + " · ".join(f"{o.value} {counts[o]}" for o in Outcome if counts[o]),
        f"**Human checks:** {sum(r.human_checks for r in reports)}",
        f"**Permission denials:** {sum(r.denials for r in reports)}",
        f"**Time:** {seconds / SECONDS_PER_MINUTE:.0f} min",
        f"**Notional cost:** ${sum(r.cost_usd for r in reports):.2f}",
    ]
    waiting = [r for r in ordered if r.outcome in NEEDS_OWNER]
    if waiting:
        lines += ["", "### Needs the owner", "", *(_needs(report) for report in waiting)]
    return "\n".join(lines) + "\n"


def _row(report: IssueReport) -> str:
    pr = f"#{report.pr}" if report.pr is not None else "-"
    minutes = f"{report.seconds / SECONDS_PER_MINUTE:.0f}"
    return (
        f"| #{report.number} | {report.outcome.value} | {pr} | {report.review_rounds} "
        f"| {report.denials} | {minutes} |"
    )


def _needs(report: IssueReport) -> str:
    target = f"#{report.pr}" if report.outcome is Outcome.WAITING_OWNER else f"#{report.number}"
    detail = report.detail.splitlines()[0] if report.detail else ""
    return f"- {target}: {report.outcome.value}. {detail}".rstrip(". ") + "."
