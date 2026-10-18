"""Which changes wait for the owner (SPEC §9.1)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from agent_batch.core import globs
from agent_batch.core.config import HIGH_RISK
from agent_batch.core.model import Issue, Risk

GENERIC_PATTERNS: tuple[str, ...] = (
    # The agents' own controls.
    ".claude/", "CLAUDE.md", ".github/", "Makefile", "scripts/",
    # Dependencies.
    "pyproject.toml", "uv.lock", "requirements*.txt", "Pipfile", "Pipfile.lock", "poetry.lock",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb",
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "Package.swift", "Package.resolved",
    "Gemfile", "Gemfile.lock",
    # Quality configuration.
    ".importlinter", "ruff.toml", ".ruff.toml", "mypy.ini", "setup.cfg", "tox.ini",
    ".pre-commit-config.yaml", ".swiftlint.yml", ".swift-format", "eslint.config.*",
    ".eslintrc*", "tsconfig*.json", "biome.json",
    # Secrets.
    ".env", ".env.*", "*.pem", "*.key",
    # Schemas and migrations.
    "**/migrations/", "schema.sql", "*.prisma",
)  # fmt: skip

RISK_HEADING = re.compile(r"^###\s+Risk\s*$", re.IGNORECASE | re.MULTILINE)
HUMAN_CHECK = re.compile(r"\bhuman\(")


def parse_patterns(text: str) -> tuple[str, ...]:
    """The patterns in a `.claude/risk-paths` file: one per line, `#` starts a comment."""
    lines = (line.strip() for line in text.splitlines())
    return tuple(line for line in lines if line and not line.startswith("#"))


def stated_risk(body: str) -> bool | None:
    """True when the issue's Risk section says high, False when low, None when neither."""
    match = RISK_HEADING.search(body)
    if match is None:
        return None
    for line in body[match.end() :].splitlines():
        word = line.strip().lower()
        if word.startswith("high"):
            return True
        if word.startswith("low"):
            return False
        if word:
            return None
    return None


def count_human_checks(body: str) -> int:
    return len(HUMAN_CHECK.findall(body))


def classify(files: Sequence[str], project_patterns: Sequence[str], issue: Issue) -> Risk:
    """High when the issue says so, it's labeled so, or a changed file matches a risk path."""
    reasons: list[str] = []
    stated = stated_risk(issue.body)
    if stated is None:
        reasons.append("the issue doesn't state its risk")
    elif stated:
        reasons.append("the issue is marked high risk")
    if HIGH_RISK in issue.labels:
        reasons.append(f"the issue is labeled {HIGH_RISK}")
    patterns = (*GENERIC_PATTERNS, *project_patterns)
    for path in files:
        pattern = globs.first_match(path, patterns)
        if pattern is not None:
            reasons.append(f"`{path}` matches `{pattern}`")
    return Risk(high=bool(reasons), reasons=tuple(reasons))
