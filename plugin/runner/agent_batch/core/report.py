"""The batch's summary and numbers (SPEC §16.2)."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Sequence

from agent_batch.core.model import IssueReport, Outcome, RunDenial

SECONDS_PER_MINUTE = 60
# The event log keeps a denial's command whole; the summary only needs enough to recognize it.
COMMAND_CHARS = 200
BACKTICKS = re.compile(r"`+")
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
        f"**Permission denials:** {sum(len(r.denials) for r in reports)}",
        f"**Time:** {seconds / SECONDS_PER_MINUTE:.0f} min",
        f"**Notional cost:** ${sum(r.cost_usd for r in reports):.2f}",
    ]
    denied = [_denial(r.number, denial) for r in ordered for denial in r.denials]
    if denied:
        lines += ["", "### Permission denials", "", *denied]
    waiting = [r for r in ordered if r.outcome in NEEDS_OWNER]
    if waiting:
        lines += ["", "### Needs the owner", "", *(_needs(report) for report in waiting)]
    return "\n".join(lines) + "\n"


def _row(report: IssueReport) -> str:
    pr = f"#{report.pr}" if report.pr is not None else "-"
    minutes = f"{report.seconds / SECONDS_PER_MINUTE:.0f}"
    return (
        f"| #{report.number} | {report.outcome.value} | {pr} | {report.review_rounds} "
        f"| {len(report.denials)} | {minutes} |"
    )


def _denial(number: int, denied: RunDenial) -> str:
    """One line per denial: a Bash command as it ran, any other tool's input as JSON."""
    command = denied.denial.tool_input.get("command")
    if isinstance(command, str):
        text = command
    else:
        text = json.dumps(denied.denial.tool_input, ensure_ascii=False)
    text = " ".join(text.splitlines())
    if len(text) > COMMAND_CHARS:
        text = text[:COMMAND_CHARS] + "…"
    return f"- #{number} {denied.run}: {denied.denial.tool} {_code(text)}"


def _code(text: str) -> str:
    """Inline code that holds any text, so an agent's `@user` or `#N` stays inert on GitHub."""
    fence = "`" * (max((len(run) for run in BACKTICKS.findall(text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _needs(report: IssueReport) -> str:
    target = f"#{report.pr}" if report.outcome is Outcome.WAITING_OWNER else f"#{report.number}"
    detail = report.detail.splitlines()[0] if report.detail else ""
    return f"- {target}: {report.outcome.value}. {detail}".rstrip(". ") + "."
