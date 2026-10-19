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
# GitHub refuses a comment over 65,536 characters; the event log keeps every denial anyway.
DENIAL_LINES = 100
# A denial is recognized by what it ran or touched; a file's content never goes to GitHub.
SHOWN_INPUTS = ("command", "file_path", "url")
BACKTICKS = re.compile(r"`+")
NEEDS_OWNER = (Outcome.WAITING_OWNER, Outcome.BLOCKED, Outcome.FAILED)
EVENT_LOG = "the batch's event log (`events.jsonl`)"


def model_lines(model: str | None, effort: str | None) -> list[str]:
    """The model and effort as the batch's comments state them, when they're set."""
    shown = (("Model", model), ("Effort", effort))
    return [f"**{name}:** {value}" for name, value in shown if value is not None]


def render(reports: Sequence[IssueReport], seconds: float, model_text: Sequence[str] = ()) -> str:
    """The summary; `model_text` holds the batch's `model_lines`."""
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
        *model_text,
    ]
    denied = [_denial(r.number, denial) for r in ordered for denial in r.denials]
    if denied:
        lines += ["", "### Permission denials", "", *denied[:DENIAL_LINES]]
    if len(denied) > DENIAL_LINES:
        more = len(denied) - DENIAL_LINES
        lines.append(f"- … and {more} more in {EVENT_LOG}")
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
    """One line per denial: its command, file or URL, else the tool's input as JSON."""
    tool_input = denied.denial.tool_input
    shown = [value for key in SHOWN_INPUTS if isinstance(value := tool_input.get(key), str)]
    text = shown[0] if shown else json.dumps(tool_input, ensure_ascii=False)
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
    """One sentence per issue; the rest of its detail, a review's findings say, is elsewhere."""
    target = f"#{report.pr}" if report.outcome is Outcome.WAITING_OWNER else f"#{report.number}"
    lines = report.detail.splitlines()
    # The first line with words in it; a detail without any reads as it did before #54.
    first, *rest = [line for line in lines if line.strip()] or lines[:1] or [""]
    line = f"- {target}: {report.outcome.value}. {first}".rstrip(":. ")
    if rest:
        line += " See " if line.endswith(("?", "!")) else "; see "
        line += EVENT_LOG if report.unannounced else f"{target}'s comment"
    return line + "."
