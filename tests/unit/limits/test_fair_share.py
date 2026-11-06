"""What one person may spend, and what their team may spend together."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.limits.fair_share import (
    Allowance,
    OverBudget,
    check_within_budget,
)

BOTH = Allowance(per_person=Decimal("5.00"), per_team=Decimal("20.00"))
PERSON_ONLY = Allowance(per_person=Decimal("5.00"), per_team=None)
NEITHER = Allowance(per_person=None, per_team=None)


class TestNothingConfigured:
    def test_anybody_may_run(self):
        assert (
            check_within_budget(
                allowance=NEITHER,
                spent_by_person=Decimal("900"),
                spent_by_team=Decimal("9000"),
            )
            is None
        )


class TestThePersonalCap:
    def test_under_it_is_fine(self):
        assert (
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("4.99"),
                spent_by_team=Decimal("0"),
            )
            is None
        )

    def test_at_it_is_refused(self):
        with pytest.raises(OverBudget):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("5.00"),
                spent_by_team=Decimal("0"),
            )

    def test_the_refusal_says_it_was_theirs(self):
        with pytest.raises(OverBudget, match="your own"):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("5.00"),
                spent_by_team=Decimal("0"),
            )

    def test_it_applies_even_when_the_team_has_room(self):
        with pytest.raises(OverBudget):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("5.00"),
                spent_by_team=Decimal("5.00"),
            )


class TestTheTeamCap:
    def test_under_it_is_fine(self):
        assert (
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("1"),
                spent_by_team=Decimal("19.99"),
            )
            is None
        )

    def test_at_it_is_refused(self):
        with pytest.raises(OverBudget):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("1"),
                spent_by_team=Decimal("20.00"),
            )

    def test_the_refusal_says_it_was_the_teams(self):
        with pytest.raises(OverBudget, match="team"):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("1"),
                spent_by_team=Decimal("20.00"),
            )

    def test_no_team_cap_means_only_the_personal_one(self):
        assert (
            check_within_budget(
                allowance=PERSON_ONLY,
                spent_by_person=Decimal("1"),
                spent_by_team=Decimal("9000"),
            )
            is None
        )


class TestWhenBothAreReached:
    def test_the_personal_one_is_reported(self):
        with pytest.raises(OverBudget, match="your own"):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("5.00"),
                spent_by_team=Decimal("20.00"),
            )


class TestWhatTheRefusalCarries:
    def test_it_says_how_much_was_spent(self):
        with pytest.raises(OverBudget, match="5"):
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("5.00"),
                spent_by_team=Decimal("0"),
            )

    def test_it_says_what_the_cap_was(self):
        found = None
        try:
            check_within_budget(
                allowance=BOTH,
                spent_by_person=Decimal("7.50"),
                spent_by_team=Decimal("0"),
            )
        except OverBudget as refused:
            found = str(refused)
        assert "7.50" in found and "5.00" in found


class TestAnAllowanceThatMakesNoSense:
    def test_a_negative_personal_cap_is_refused(self):
        with pytest.raises(ValueError):
            Allowance(per_person=Decimal("-1"), per_team=None)

    def test_a_team_cap_below_the_personal_one_is_refused(self):
        with pytest.raises(ValueError):
            Allowance(per_person=Decimal("10"), per_team=Decimal("5"))

    def test_equal_caps_are_allowed(self):
        assert Allowance(per_person=Decimal("5"), per_team=Decimal("5"))

    def test_a_cap_of_zero_is_allowed(self):
        assert Allowance(per_person=Decimal("0"), per_team=None)
