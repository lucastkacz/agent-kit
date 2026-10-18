"""Validates the plugin and its marketplace with Claude Code, failing on any error or warning.

The one warning let through is the missing `version`: without one, projects pick up every change
that merges here (SPEC §16.1), which is what the kit wants.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

ALLOWED_WARNINGS = frozenset({"version"})


def problems(report: dict[str, Any], target: str) -> list[str]:
    """The errors and warnings in a `claude plugin validate --json` report that count."""
    sections = [report.get("manifest") or {}, *(report.get("contents") or [])]
    found: list[str] = []
    for section in sections:
        for kind in ("errors", "warnings"):
            for item in section.get(kind) or []:
                path = str(item.get("path") or "")
                if kind == "warnings" and path.rsplit(" ", 1)[-1] in ALLOWED_WARNINGS:
                    continue
                found.append(f"{target}: {kind[:-1]} at {path or '-'}: {item.get('message')}")
    return found


def validate(target: str) -> list[str]:
    done = subprocess.run(
        ["claude", "plugin", "validate", target, "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(done.stdout)
    except json.JSONDecodeError:
        return [f"{target}: claude plugin validate failed: {done.stderr.strip() or done.stdout}"]
    return problems(report, target)


def main(targets: list[str]) -> int:
    found = [problem for target in targets for problem in validate(target)]
    for problem in found:
        print(problem)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
