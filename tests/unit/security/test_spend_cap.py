"""A ceiling on what one run may cost in money."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.spend_cap import SpendCap


def cap(**over) -> SpendCap:
    settings = {"warn_at": Decimal("0.50"), "refuse_at": Decimal("1.00")}
    settings.update(over)
    return SpendCap(**settings)


class TestWhileItIsAffordable:
    def test_nothing_is_said_at_the_start(self):
        assert cap().check(Decimal("0")) is None

    def test_nothing_is_said_well_under_the_warning(self):
        assert cap().check(Decimal("0.10")) is None

    def test_nothing_is_said_just_under_the_warning(self):
        assert cap().check(Decimal("0.4999")) is None


class TestTheWarning:
    def test_warns_on_reaching_the_soft_threshold(self):
        warned = cap().check(Decimal("0.50"))
        assert warned is not None and warned.refuse is False

    def test_the_warning_names_what_has_been_spent(self):
        assert "0.50" in cap().check(Decimal("0.50")).message

    def test_the_warning_names_the_ceiling(self):
        assert "1.00" in cap().check(Decimal("0.50")).message

    def test_it_warns_once_rather_than_on_every_call(self):
        one = cap()
        assert one.check(Decimal("0.50")) is not None
        assert one.check(Decimal("0.60")) is None


class TestTheRefusal:
    def test_refuses_on_reaching_the_hard_threshold(self):
        stopped = cap().check(Decimal("1.00"))
        assert stopped is not None and stopped.refuse is True

    def test_the_refusal_names_the_ceiling_it_hit(self):
        assert "1.00" in cap().check(Decimal("1.00")).message

    def test_it_refuses_every_time_once_it_has(self):
        """A warning is said once; a refusal is a standing answer."""
        one = cap()
        assert one.check(Decimal("1.50")).refuse is True
        assert one.check(Decimal("1.60")).refuse is True

    def test_crossing_straight_past_the_warning_still_refuses(self):
        assert cap().check(Decimal("5.00")).refuse is True


class TestWhatADeploymentCanTurnOff:
    def test_no_ceiling_means_no_refusal(self):
        assert cap(refuse_at=None).check(Decimal("100")) is None or (
            cap(refuse_at=None).check(Decimal("100")).refuse is False
        )

    def test_no_warning_still_refuses_at_the_ceiling(self):
        assert cap(warn_at=None).check(Decimal("1.00")).refuse is True

    def test_neither_set_says_nothing_at_all(self):
        assert cap(warn_at=None, refuse_at=None).check(Decimal("999")) is None


class TestADeploymentThatCannotPrice:
    def test_an_unpriced_run_is_not_refused_on_a_guess(self):
        """Pricing nothing at zero would make every ceiling unreachable;"""
        assert cap().check(None) is None


def test_a_ceiling_below_its_warning_is_refused_as_configuration():
    with pytest.raises(ValueError, match="warn_at"):
        SpendCap(warn_at=Decimal("2.00"), refuse_at=Decimal("1.00"))


class TestHowADeploymentDeclaresIt:
    """Amounts are written as strings so a price never goes via a float."""

    def test_it_is_off_unless_a_ceiling_is_set(self):
        from agent.src.agent.config.middleware import SpendLimitConfig

        assert SpendLimitConfig().enabled is False

    def test_setting_a_ceiling_turns_it_on(self):
        from agent.src.agent.config.middleware import SpendLimitConfig

        assert SpendLimitConfig(refuse_at="1.00").enabled is True

    def test_amounts_are_read_as_exact_decimals(self):
        from agent.src.agent.config.middleware import SpendLimitConfig

        assert SpendLimitConfig(refuse_at="0.10").ceiling() == Decimal("0.10")

    def test_no_ceiling_reads_as_none(self):
        from agent.src.agent.config.middleware import SpendLimitConfig

        assert SpendLimitConfig().ceiling() is None

    def test_an_unreadable_amount_is_refused_rather_than_ignored(self):
        from agent.src.agent.config.middleware import SpendLimitConfig

        with pytest.raises(ValueError):
            SpendLimitConfig(refuse_at="one pound").ceiling()


class TestAmountsAreReadable:
    """A limit shown as `2E-7` is a limit nobody can check against."""

    def test_a_small_ceiling_is_not_written_in_scientific_notation(self):
        said = SpendCap(refuse_at=Decimal("0.0000002")).check(Decimal("0.5")).message
        assert "0.0000002" in said and "E-7" not in said

    def test_a_small_amount_spent_is_not_either(self):
        said = (
            SpendCap(refuse_at=Decimal("0.0000001")).check(Decimal("0.0000003")).message
        )
        assert "E-" not in said

    def test_an_ordinary_amount_is_unchanged(self):
        assert "1.00" in SpendCap(refuse_at=Decimal("1.00")).check(Decimal("2")).message

    def test_the_warning_is_readable_too(self):
        said = (
            SpendCap(warn_at=Decimal("0.0000001"), refuse_at=Decimal("0.0000002"))
            .check(Decimal("0.00000015"))
            .message
        )
        assert "E-" not in said


class TestAnAmountSaysWhatItIsIn:
    """`0.05` is not an amount. A figure without its unit cannot be"""

    def test_the_refusal_names_the_currency(self):
        said = cap(currency="USD").check(Decimal("1.00")).message
        assert "USD" in said

    def test_the_warning_names_the_currency(self):
        said = cap(currency="EUR").check(Decimal("0.50")).message
        assert "EUR" in said

    def test_the_currency_sits_with_the_figure(self):
        said = cap(currency="GBP").check(Decimal("1.00")).message
        assert "1.00 GBP" in said

    def test_a_deployment_that_names_no_currency_still_gets_a_message(self):
        said = cap().check(Decimal("1.00")).message
        assert "1.00" in said
