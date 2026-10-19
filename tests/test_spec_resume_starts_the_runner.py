"""SPEC §11.3 says that resuming a batch starts its runner again (#100)."""

from __future__ import annotations

from test_spec_cloud_e2e_and_routines import spec_section

CONTROL_TOWER = "11.3 The control tower and notifications"


def test_spec_11_3_says_resuming_a_batch_starts_its_runner_again() -> None:
    section = spec_section(CONTROL_TOWER)
    assert "resuming the batch starts its runner again" in section, section
    assert "the lane issues it didn't finish go to the next batch" not in section, section
