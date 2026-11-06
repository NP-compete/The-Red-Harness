"""Deciding who pays for a run."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.cost_attribution import Charge, RunCost, attribute


def run(**kwargs) -> RunCost:
    defaults = {
        "run_id": "r1",
        "person": "ana",
        "team": "finance",
        "project": "quarterly",
        "amount": Decimal("1.50"),
        "subagent_amounts": {},
        "started_by": "person",
    }
    defaults.update(kwargs)
    return RunCost(**defaults)


def test_a_run_is_charged_to_its_project():
    assert attribute(run()).charged_to == "quarterly"


def test_a_run_without_a_project_falls_back_to_the_team():
    assert attribute(run(project="")).charged_to == "finance"


def test_a_run_without_a_team_falls_back_to_the_person():
    assert attribute(run(project="", team="")).charged_to == "ana"


def test_the_amount_charged_is_the_run_total():
    assert attribute(run()).amount == Decimal("1.50")


def test_work_done_by_subagents_is_included():
    charged = attribute(run(subagent_amounts={"researcher": Decimal("0.75")}))
    assert charged.amount == Decimal("2.25")


def test_subagent_costs_are_broken_out_rather_than_hidden():
    charged = attribute(run(subagent_amounts={"researcher": Decimal("0.75")}))
    assert charged.breakdown["researcher"] == Decimal("0.75")


def test_the_main_run_appears_in_the_breakdown_too():
    charged = attribute(run(subagent_amounts={"researcher": Decimal("0.75")}))
    assert charged.breakdown["main"] == Decimal("1.50")


def test_the_breakdown_adds_up_to_the_total():
    charged = attribute(
        run(subagent_amounts={"a": Decimal("0.25"), "b": Decimal("0.25")})
    )
    assert sum(charged.breakdown.values()) == charged.amount


def test_a_scheduled_run_is_charged_to_the_team_not_the_person():
    scheduled = run(project="", started_by="schedule")
    assert attribute(scheduled).charged_to == "finance"


def test_a_scheduled_run_with_no_team_is_charged_to_the_platform():
    scheduled = run(project="", team="", started_by="schedule")
    assert attribute(scheduled).charged_to == "platform"


def test_who_ran_it_is_recorded_whoever_pays():
    assert attribute(run(project="shared")).person == "ana"


def test_money_is_rounded_to_pennies():
    charged = attribute(run(amount=Decimal("1.005"), subagent_amounts={}))
    assert charged.amount.as_tuple().exponent == -2


def test_a_free_run_is_still_attributed():
    assert attribute(run(amount=Decimal("0"))).charged_to == "quarterly"


def test_a_free_run_charges_nothing():
    assert attribute(run(amount=Decimal("0"))).amount == Decimal("0.00")


def test_a_negative_amount_is_refused():
    with pytest.raises(ValueError):
        run(amount=Decimal("-1"))


def test_a_negative_subagent_amount_is_refused():
    with pytest.raises(ValueError):
        run(subagent_amounts={"a": Decimal("-1")})


def test_a_run_with_nobody_at_all_is_refused():
    with pytest.raises(ValueError):
        run(person=" ", team="", project="")


def test_a_charge_can_be_summed_with_others():
    charges = [attribute(run()), attribute(run(run_id="r2", amount=Decimal("2.50")))]
    assert sum(charge.amount for charge in charges) == Decimal("4.00")


def test_a_charge_is_a_record_not_a_calculation_to_repeat():
    assert isinstance(attribute(run()), Charge)
