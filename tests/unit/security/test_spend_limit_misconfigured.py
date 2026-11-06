"""A ceiling that cannot be read must not quietly become no ceiling."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.agent.config.middleware import SpendLimitConfig
from agent.src.infrastructure.middleware import (
    SpendLimitUnusable,
    _build_spend_limit,
)


def test_a_usable_ceiling_builds():
    assert _build_spend_limit(SpendLimitConfig(refuse_at="1.00")) is not None


def test_an_unreadable_amount_refuses_rather_than_dropping_the_cap():
    with pytest.raises(SpendLimitUnusable, match="tuppence"):
        _build_spend_limit(SpendLimitConfig(refuse_at="tuppence"))


def test_a_warning_above_the_ceiling_refuses():
    with pytest.raises(SpendLimitUnusable):
        _build_spend_limit(SpendLimitConfig(warn_at="2.00", refuse_at="1.00"))


def test_the_refusal_says_what_to_fix():
    with pytest.raises(SpendLimitUnusable, match="spend_limit"):
        _build_spend_limit(SpendLimitConfig(refuse_at="tuppence"))


def test_a_deployment_with_no_ceiling_is_untouched():
    """Not configured is not misconfigured."""
    assert _build_spend_limit(SpendLimitConfig()) is None


class TestCountingForACallerCapWithNoRunCap:
    """A per-caller cap read at the door and never written to"""

    @staticmethod
    def _built(*, run_cap, caller_cap):
        from unittest.mock import patch

        from agent.src.security.inbound_limits import Limits

        limits = (
            Limits(per_second=1, burst=1, daily_spend=Decimal("5"))
            if caller_cap
            else None
        )

        class _Inbound:
            def __init__(self):
                self.limits = limits

        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
            return_value=_Inbound(),
        ):
            config = (
                SpendLimitConfig(refuse_at="1.00")
                if run_cap
                else SpendLimitConfig(enabled=False)
            )
            return _build_spend_limit(config)

    def test_a_caller_cap_alone_still_builds_something_that_counts(self):
        built = self._built(run_cap=False, caller_cap=True)
        assert built is not None

    def test_and_it_does_not_cap_the_run(self):
        built = self._built(run_cap=False, caller_cap=True)
        assert built._cap.refuse_at is None

    def test_neither_cap_builds_nothing(self):
        assert self._built(run_cap=False, caller_cap=False) is None

    def test_a_run_cap_alone_still_builds(self):
        assert self._built(run_cap=True, caller_cap=False) is not None


class TestCountingForAnEverydayAllowance:
    """The allowance is enforced at the door and needs a"""

    @staticmethod
    def _built(*, person_cap):
        from decimal import Decimal
        from unittest.mock import patch

        from agent.src.limits.fair_share import Allowance

        allowance = Allowance(
            per_person=Decimal("5") if person_cap else None, per_team=None
        )

        class _Inbound:
            limits = None

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=_Inbound(),
            ),
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_limits_config",
                return_value=allowance,
            ),
        ):
            return _build_spend_limit(SpendLimitConfig(enabled=False))

    def test_an_allowance_alone_still_builds_something_that_counts(self):
        assert self._built(person_cap=True) is not None

    def test_no_allowance_and_no_run_cap_builds_nothing(self):
        assert self._built(person_cap=False) is None
