"""accept-batch reads long cloud logs through its agent and names the issues it opens (#80, #213).

Each test checks the few words that carry the behavior, so rewording the skill doesn't break it.
"""

from __future__ import annotations

import re

from test_skill_accept_batch import section, text


def has(text: str, *tokens: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, (missing, text)


def test_it_reads_a_cloud_log_page_by_page_with_an_agent_that_reports_what_matters() -> None:
    gather = section("Gather everything")
    has(gather, "page by page", "`agent-kit:routines` type")
    has(gather, "denials", "owner's messages", "writes outside the sandbox")


def step(heading: str) -> int:
    found = re.search(rf"^## (\d+)\. {re.escape(heading)}", text(), re.MULTILINE)
    assert found is not None, f"no section `## <n>. {heading}`"
    return int(found.group(1))


def test_it_opens_the_approved_issues_before_it_posts_the_comment_that_names_them() -> None:
    opened, recorded = step("Open the approved issues"), step("Record the acceptance")
    assert opened < recorded, (opened, recorded)
    has(section("Record the acceptance"), f"the issues opened in step {opened}")
