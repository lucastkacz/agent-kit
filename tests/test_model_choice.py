"""The edges of a batch's model and effort (#56)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agent_batch.core import plan
from agent_batch.core.plan import BatchPlan, PlanError
from conftest import World

MODELS = st.one_of(st.none(), st.sampled_from(("opus", "sonnet", "claude-opus-5-5", "opus[1m]")))
EFFORTS = st.one_of(st.none(), st.sampled_from(plan.EFFORTS))


@given(MODELS, EFFORTS, MODELS, EFFORTS)
def test_each_flag_overrides_only_its_own_part_of_the_model_line(
    flag_model: str | None, flag_effort: str | None, line_model: str | None, line_effort: str | None
) -> None:
    batch = BatchPlan(lanes=((1,),), model=line_model, effort=line_effort)
    chosen = plan.choose_model(flag_model, flag_effort, batch)
    assert chosen == (
        flag_model if flag_model is not None else line_model,
        flag_effort if flag_effort is not None else line_effort,
    )


@pytest.mark.parametrize("model", ["opus", "claude-opus-5-5", "opus[1m]", "claude-sonnet-4.5"])
def test_a_model_line_takes_an_alias_or_a_full_name(model: str) -> None:
    assert plan.parse_plan(f"Lane 1: #1\nModel: {model}, high\n").model == model


@pytest.mark.parametrize(
    "line", ["Model:", "Model: opus max", "Model: `opus`", "Model: -opus", "Model: opus, High"]
)
def test_a_model_line_that_cant_be_read_stops_the_batch(line: str) -> None:
    with pytest.raises(PlanError, match="`Model:` needs a model"):
        plan.parse_plan(f"Lane 1: #1\n{line}\n")


@pytest.mark.parametrize("model", ["", "two words", "-opus"])
def test_the_model_flag_refuses_what_isnt_a_model(
    world: World, capsys: pytest.CaptureFixture[str], model: str
) -> None:
    world.add_batch(1, "Lane 1: #10\n")

    with pytest.raises(SystemExit) as exited:
        world.run("run", "1", "--model", model)

    assert exited.value.code == 2
    assert world.gh()["calls"] == []
    assert "--model" in capsys.readouterr().err
