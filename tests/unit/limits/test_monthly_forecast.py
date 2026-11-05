"""Where the month is heading, said while there is still a month left."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from agent.src.limits.fair_share import Allowance
from agent.src.limits.report import describe_allowance

MARCH = date(2026, 3, 10)


def _report(**kwargs):
    allowance = kwargs.pop(
        "allowance",
        Allowance(per_person=None, per_team=None, per_person_month=Decimal("100.00")),
    )
    return describe_allowance(
        allowance=allowance,
        spent_by_person=kwargs.pop("spent_by_person", Decimal("0")),
        spent_by_team=kwargs.pop("spent_by_team", Decimal("0")),
        month_by_person=kwargs.pop("month_by_person", Decimal("0")),
        month_by_team=kwargs.pop("month_by_team", Decimal("0")),
        today=kwargs.pop("today", MARCH),
        **kwargs,
    )


class TestWhenThereIsNoMonthlyCap:
    def test_there_is_no_forecast(self):
        found = _report(allowance=Allowance(per_person=Decimal("5.00"), per_team=None))
        assert found["forecast"]["person"] is None

    def test_the_daily_report_is_unchanged(self):
        found = _report(
            allowance=Allowance(per_person=Decimal("5.00"), per_team=None),
            spent_by_person=Decimal("1.00"),
        )
        assert found["person"]["remaining"] == "4.00"


class TestOnTrack:
    def test_a_quiet_month_is_on_track(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert found["forecast"]["person"]["verdict"] == "on-track"

    def test_it_says_the_daily_burn(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert found["forecast"]["person"]["per_day"] == "1.00"

    def test_it_says_what_the_month_will_come_to(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert found["forecast"]["person"]["projected_total"] == "31.00"

    def test_on_track_names_no_date(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert found["forecast"]["person"]["exhausted_on"] is None


class TestHeadingOver:
    def test_a_heavy_month_will_overrun(self):
        found = _report(month_by_person=Decimal("60.00"))
        assert found["forecast"]["person"]["verdict"] == "will-overrun"

    def test_it_names_the_day_the_budget_runs_out(self):
        found = _report(month_by_person=Decimal("60.00"))
        assert found["forecast"]["person"]["exhausted_on"] == "2026-03-16"

    def test_it_says_how_much_is_left(self):
        found = _report(month_by_person=Decimal("60.00"))
        assert found["forecast"]["person"]["remaining"] == "40.00"


class TestAlreadyOver:
    def test_a_spent_budget_says_so(self):
        found = _report(month_by_person=Decimal("120.00"))
        assert found["forecast"]["person"]["verdict"] == "exhausted"

    def test_nothing_remains(self):
        found = _report(month_by_person=Decimal("120.00"))
        assert found["forecast"]["person"]["remaining"] == "0.00"


class TestTheTeam:
    def test_a_team_month_is_forecast_too(self):
        found = _report(
            allowance=Allowance(
                per_person=None,
                per_team=None,
                per_team_month=Decimal("900.00"),
                teams=("research",),
            ),
            month_by_team=Decimal("600.00"),
        )
        assert found["forecast"]["team"]["verdict"] == "will-overrun"

    def test_somebody_in_no_team_gets_no_team_forecast(self):
        found = _report(
            allowance=Allowance(
                per_person=None,
                per_team=None,
                per_team_month=Decimal("900.00"),
                teams=("research",),
            ),
            month_by_team=Decimal("600.00"),
            in_a_team=False,
        )
        assert found["forecast"]["team"] is None


class TestTheNumbersAreStrings:
    def test_money_does_not_come_back_as_a_float(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert all(
            isinstance(found["forecast"]["person"][field], str)
            for field in ("per_day", "projected_total", "remaining", "spent", "limit")
        )

    def test_the_month_so_far_is_reported(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert found["forecast"]["person"]["spent"] == "10.00"

    def test_the_budget_is_reported(self):
        found = _report(month_by_person=Decimal("10.00"))
        assert found["forecast"]["person"]["limit"] == "100.00"


class TestItNeverCostsTheRestOfThePage:
    def test_a_forecast_that_cannot_be_made_leaves_the_rest_standing(self):
        found = describe_allowance(
            allowance=Allowance(
                per_person=Decimal("5.00"),
                per_team=None,
                per_person_month=Decimal("100"),
            ),
            spent_by_person=Decimal("1.00"),
            spent_by_team=Decimal("0"),
            month_by_person=Decimal("10.00"),
            month_by_team=Decimal("0"),
            today="not a date",
        )
        assert found["person"]["remaining"] == "4.00"
        assert found["forecast"]["person"] is None

    def test_the_old_callers_still_work(self):
        found = describe_allowance(
            allowance=Allowance(per_person=Decimal("5.00"), per_team=None),
            spent_by_person=Decimal("1.00"),
            spent_by_team=Decimal("0"),
        )
        assert found["person"]["remaining"] == "4.00"
