"""Telling somebody what they have left, before they are refused."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.limits.fair_share import Allowance
from agent.src.limits.report import describe_allowance

BOTH = Allowance(per_person=Decimal("5.00"), per_team=Decimal("20.00"))


class TestWhatIsReported:
    @staticmethod
    def _said(**kwargs):
        return describe_allowance(
            allowance=kwargs.pop("allowance", BOTH),
            spent_by_person=kwargs.pop("spent_by_person", Decimal("1.25")),
            spent_by_team=kwargs.pop("spent_by_team", Decimal("8.00")),
            **kwargs,
        )

    def test_what_they_have_spent(self):
        assert self._said()["person"]["spent"] == "1.25"

    def test_what_they_may_spend(self):
        assert self._said()["person"]["limit"] == "5.00"

    def test_what_is_left(self):
        assert self._said()["person"]["remaining"] == "3.75"

    def test_the_team_too(self):
        assert self._said()["team"]["remaining"] == "12.00"

    def test_amounts_are_strings_not_floats(self):
        for side in ("person", "team"):
            assert isinstance(self._said()[side]["spent"], str)


class TestWhenThereIsNoCap:
    def test_a_person_with_no_cap_is_said_to_have_none(self):
        found = describe_allowance(
            allowance=Allowance(per_person=None, per_team=None),
            spent_by_person=Decimal("3"),
            spent_by_team=Decimal("3"),
        )
        assert found["person"]["limit"] is None

    def test_and_has_no_remaining_rather_than_zero(self):
        found = describe_allowance(
            allowance=Allowance(per_person=None, per_team=None),
            spent_by_person=Decimal("3"),
            spent_by_team=Decimal("3"),
        )
        assert found["person"]["remaining"] is None

    def test_spending_is_still_reported(self):
        found = describe_allowance(
            allowance=Allowance(per_person=None, per_team=None),
            spent_by_person=Decimal("3"),
            spent_by_team=Decimal("3"),
        )
        assert found["person"]["spent"] == "3"

    def test_no_team_is_reported_as_absent(self):
        found = describe_allowance(
            allowance=Allowance(per_person=Decimal("5"), per_team=None),
            spent_by_person=Decimal("1"),
            spent_by_team=Decimal("0"),
            in_a_team=False,
        )
        assert found["team"] is None


class TestWhenTheyAreNearlyOut:
    @pytest.mark.parametrize(
        "spent,expected", [("4.49", False), ("4.50", True), ("5.00", True)]
    )
    def test_it_is_flagged_before_the_refusal(self, spent, expected):
        found = describe_allowance(
            allowance=BOTH,
            spent_by_person=Decimal(spent),
            spent_by_team=Decimal("0"),
        )
        assert found["person"]["nearly_out"] is expected

    def test_a_person_with_no_cap_is_never_nearly_out(self):
        found = describe_allowance(
            allowance=Allowance(per_person=None, per_team=None),
            spent_by_person=Decimal("900"),
            spent_by_team=Decimal("900"),
        )
        assert found["person"]["nearly_out"] is False


class TestOverspending:
    def test_remaining_never_goes_below_nothing(self):
        found = describe_allowance(
            allowance=BOTH,
            spent_by_person=Decimal("7.50"),
            spent_by_team=Decimal("0"),
        )
        assert found["person"]["remaining"] == "0.00"


class TestSubCentPrecisionSurvives:
    """A rate card may price in fractions of a cent."""

    def test_the_caps_own_precision_is_kept(self):
        fine = Allowance(per_person=Decimal("0.0500"), per_team=None)
        found = describe_allowance(
            allowance=fine,
            spent_by_person=Decimal("0.0125"),
            spent_by_team=Decimal("0"),
        )
        assert found["person"]["remaining"] == "0.0375"

    def test_nothing_left_is_reported_at_that_precision_too(self):
        fine = Allowance(per_person=Decimal("0.0500"), per_team=None)
        found = describe_allowance(
            allowance=fine,
            spent_by_person=Decimal("1"),
            spent_by_team=Decimal("0"),
        )
        assert found["person"]["remaining"] == "0.0000"
