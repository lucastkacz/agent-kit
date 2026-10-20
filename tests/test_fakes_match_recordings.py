"""The fakes answer in the shapes the real tools answered in the contract tests (small tests).

`make contract` records the real answers. When `gh` or `claude` change theirs, this test fails
until the fakes catch up.
"""

from __future__ import annotations

import json

import pytest

from recorded_answers import FIELDS, MISSING, RECORDED, fake_answer, kind, pluck


@pytest.mark.parametrize("name", sorted(FIELDS))
def test_the_fake_answers_like_the_real_tool(name: str) -> None:
    recorded = json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))
    fake = fake_answer(name)
    for field in FIELDS[name]:
        real = pluck(recorded, field)
        assert real is not MISSING, f"the real {name} has no {field}, which the runner reads"
        assert kind(pluck(fake, field)) == kind(real), f"{name}: {field}"
