"""What one caller may spend before it is somebody else's turn."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.inbound_limits import Limits, admit

OPEN = Limits(per_second=10, burst=10, daily_spend=Decimal("5.00"))


class TestWhenNothingIsConfigured:
    def test_a_caller_is_admitted(self):
        assert admit("svc-a", limits=None, rate_ok=True, spent=Decimal("0")).allowed

    def test_even_one_that_has_spent_a_fortune(self):
        found = admit("svc-a", limits=None, rate_ok=True, spent=Decimal("900"))
        assert found.allowed


class TestTheRateLimit:
    def test_a_caller_within_it_is_admitted(self):
        assert admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("0")).allowed

    def test_a_caller_over_it_is_refused(self):
        assert not admit(
            "svc-a", limits=OPEN, rate_ok=False, spent=Decimal("0")
        ).allowed

    def test_the_refusal_says_it_was_the_rate(self):
        found = admit("svc-a", limits=OPEN, rate_ok=False, spent=Decimal("0"))
        assert "rate" in found.reason.lower()

    def test_the_refusal_says_when_to_come_back(self):
        found = admit(
            "svc-a", limits=OPEN, rate_ok=False, spent=Decimal("0"), retry_after=2.5
        )
        assert found.retry_after == 2.5


class TestTheSpendCap:
    def test_a_caller_under_it_is_admitted(self):
        found = admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("4.99"))
        assert found.allowed

    def test_a_caller_at_it_is_refused(self):
        found = admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("5.00"))
        assert not found.allowed

    def test_a_caller_over_it_is_refused(self):
        found = admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("5.01"))
        assert not found.allowed

    def test_the_refusal_says_it_was_the_budget(self):
        found = admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("5.00"))
        assert "spend" in found.reason.lower() or "budget" in found.reason.lower()

    def test_the_refusal_says_what_the_cap_was(self):
        found = admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("5.00"))
        assert "5" in found.reason

    def test_it_comes_back_tomorrow_not_in_seconds(self):
        found = admit("svc-a", limits=OPEN, rate_ok=True, spent=Decimal("5.00"))
        assert found.retry_after >= 60

    def test_no_cap_set_means_no_cap(self):
        only_rate = Limits(per_second=10, burst=10, daily_spend=None)
        found = admit("svc-a", limits=only_rate, rate_ok=True, spent=Decimal("900"))
        assert found.allowed


class TestWhenBothAreExceeded:
    def test_the_budget_is_the_one_reported(self):
        found = admit("svc-a", limits=OPEN, rate_ok=False, spent=Decimal("9"))
        assert "spend" in found.reason.lower() or "budget" in found.reason.lower()


class TestWhoTheCallerIs:
    def test_a_caller_with_no_identity_is_refused(self):
        assert not admit("", limits=OPEN, rate_ok=True, spent=Decimal("0")).allowed

    def test_and_said_plainly(self):
        found = admit("", limits=OPEN, rate_ok=True, spent=Decimal("0"))
        assert "identif" in found.reason.lower() or "caller" in found.reason.lower()

    def test_an_unidentified_caller_is_fine_when_nothing_is_configured(self):
        assert admit("", limits=None, rate_ok=True, spent=Decimal("0")).allowed


class TestTheLimitsThemselves:
    def test_a_rate_of_zero_is_refused_at_construction(self):
        with pytest.raises(ValueError):
            Limits(per_second=0, burst=1, daily_spend=None)

    def test_a_negative_cap_is_refused_at_construction(self):
        with pytest.raises(ValueError):
            Limits(per_second=1, burst=1, daily_spend=Decimal("-1"))

    def test_a_cap_of_zero_is_allowed(self):
        assert Limits(per_second=1, burst=1, daily_spend=Decimal("0"))
