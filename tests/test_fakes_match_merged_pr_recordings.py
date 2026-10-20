"""The fake `gh` lists merged PRs in the shape the real one recorded (#178, from #133).

`make contract` records the real lists. When the fake drifts from them, `make check` fails.
"""

from __future__ import annotations

import json

from recorded_answers import FIELDS, MISSING, RECORDED, fake_answer, kind, pluck

MERGED_LISTS = ("gh-pr-list-merged", "gh-pr-list-recent-merged")
MERGED_FIELDS = ("[].number", "[].headRefName", "[].headRefOid")


def test_the_fake_lists_merged_prs_like_the_real_gh() -> None:
    for name in MERGED_LISTS:
        assert FIELDS[name] == MERGED_FIELDS
        recorded = json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))
        fake = fake_answer(name)
        for field in MERGED_FIELDS:
            real = pluck(recorded, field)
            assert real is not MISSING, f"the real {name} has no {field}, which the runner reads"
            assert kind(pluck(fake, field)) == kind(real), f"{name}: {field}"


def test_a_leading_brackets_read_the_first_item_of_a_top_level_list() -> None:
    listed = [{"number": 93, "headRefName": "75-ship", "headRefOid": "483d5f7"}]

    assert pluck(listed, "[].number") == 93
    assert pluck([{"number": 93}], "[].headRefOid") is MISSING
    assert pluck([], "[].number") is MISSING
