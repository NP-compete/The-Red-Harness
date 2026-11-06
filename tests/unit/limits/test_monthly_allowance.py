"""A budget for the month, beside the one for the day."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.limits.config import LimitsMisconfigured, read_limits
from agent.src.limits.fair_share import Allowance


class TestReadingAMonthlyCap:
    def test_a_personal_monthly_cap_is_read(self):
        found = read_limits({"limits": {"per_person": {"monthly_spend": "100.00"}}})
        assert found.per_person_month == Decimal("100.00")

    def test_a_team_monthly_cap_is_read(self):
        found = read_limits(
            {"limits": {"per_team": {"monthly_spend": "900.00", "teams": ["research"]}}}
        )
        assert found.per_team_month == Decimal("900.00")

    def test_no_monthly_cap_means_no_monthly_cap(self):
        found = read_limits({"limits": {"per_person": {"daily_spend": "5.00"}}})
        assert found.per_person_month is None

    def test_a_daily_cap_still_works_on_its_own(self):
        found = read_limits({"limits": {"per_person": {"daily_spend": "5.00"}}})
        assert found.per_person == Decimal("5.00")

    def test_both_can_be_set_together(self):
        found = read_limits(
            {
                "limits": {
                    "per_person": {"daily_spend": "5.00", "monthly_spend": "100.00"}
                }
            }
        )
        assert (found.per_person, found.per_person_month) == (
            Decimal("5.00"),
            Decimal("100.00"),
        )

    def test_a_monthly_cap_alone_is_enough(self):
        found = read_limits({"limits": {"per_person": {"monthly_spend": "100.00"}}})
        assert found.per_person is None


class TestAMonthlyCapThatCannotBeMet:
    def test_a_monthly_cap_below_the_daily_one_is_refused(self):
        with pytest.raises(LimitsMisconfigured):
            read_limits(
                {
                    "limits": {
                        "per_person": {"daily_spend": "50.00", "monthly_spend": "10.00"}
                    }
                }
            )

    def test_the_complaint_names_both_numbers(self):
        with pytest.raises(LimitsMisconfigured) as refused:
            read_limits(
                {
                    "limits": {
                        "per_person": {"daily_spend": "50.00", "monthly_spend": "10.00"}
                    }
                }
            )
        assert "50.00" in str(refused.value) and "10.00" in str(refused.value)

    def test_equal_is_allowed(self):
        found = read_limits(
            {
                "limits": {
                    "per_person": {"daily_spend": "10.00", "monthly_spend": "10.00"}
                }
            }
        )
        assert found.per_person_month == Decimal("10.00")

    def test_a_monthly_cap_below_zero_is_refused(self):
        with pytest.raises(LimitsMisconfigured):
            read_limits({"limits": {"per_person": {"monthly_spend": "-1"}}})

    def test_something_that_is_not_an_amount_is_refused(self):
        with pytest.raises(LimitsMisconfigured):
            read_limits({"limits": {"per_person": {"monthly_spend": "soon"}}})


class TestTheAllowanceItself:
    def test_a_team_month_below_a_person_month_is_refused(self):
        with pytest.raises(ValueError):
            Allowance(
                per_person=None,
                per_team=None,
                per_person_month=Decimal("100"),
                per_team_month=Decimal("50"),
            )

    def test_the_monthly_caps_default_to_nothing(self):
        found = Allowance(per_person=None, per_team=None)
        assert (found.per_person_month, found.per_team_month) == (None, None)
