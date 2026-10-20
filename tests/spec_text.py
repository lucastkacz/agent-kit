"""What tests of the SPEC's text share: its sections, as written or flattened."""

from __future__ import annotations

import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"


def spec_section(heading: str) -> str:
    """The SPEC's `### <heading>` section, up to the next heading."""
    return SPEC.read_text(encoding="utf-8").split(f"\n### {heading}\n", 1)[1].split("\n#", 1)[0]


def flat(text: str, start_marker: str, end_marker: str) -> str:
    """The text from one marker to the next, lowercase and on one line, whatever the wrapping."""
    start = text.index(start_marker)
    end = text.find(end_marker, start + 1)
    return re.sub(r"\s+", " ", text[start : end if end != -1 else len(text)]).lower()


def flat_spec_section(heading: str) -> str:
    """The SPEC's `### <heading>` section, flattened as `flat` does."""
    return flat(SPEC.read_text(encoding="utf-8"), f"### {heading}", "\n#")


def zero_prompts() -> str:
    """SPEC §10.1 in lowercase, on one line, so that a check doesn't depend on wrapping."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("### 10.1 Zero prompts during a batch")
    end = text.index("\n### ", start + 1)
    return re.sub(r"\s+", " ", text[start:end]).lower()
