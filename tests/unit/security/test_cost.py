"""Turning token counts into money, with the rate that applied at the time."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.security.cost import ModelRate, RateCard, RunCost

CARD = RateCard(
    version="2026-10",
    rates={
        "small": ModelRate(input_per_1k="0.0005", output_per_1k="0.0015"),
        "large": ModelRate(input_per_1k="0.01", output_per_1k="0.03"),
    },
)


def test_a_known_model_is_priced():
    assert CARD.price("small", input_tokens=1000, output_tokens=1000) == Decimal(
        "0.0020"
    )


def test_pricing_is_proportional_to_tokens():
    assert CARD.price("large", input_tokens=500, output_tokens=0) == Decimal("0.005")


def test_an_unknown_model_is_unpriced_rather_than_free():
    assert CARD.price("unheard-of", input_tokens=1000, output_tokens=1000) is None


def test_money_is_exact_rather_than_floating():
    assert isinstance(CARD.price("small", input_tokens=1, output_tokens=0), Decimal)


def test_a_run_totals_across_models():
    cost = RunCost(CARD)
    cost.record("small", input_tokens=1000, output_tokens=1000)
    cost.record("large", input_tokens=1000, output_tokens=0)
    assert cost.total == Decimal("0.0120")


def test_a_run_remembers_which_rate_card_priced_it():
    cost = RunCost(CARD)
    cost.record("small", input_tokens=10, output_tokens=10)
    assert cost.rate_card_version == "2026-10"


def test_an_unpriced_model_is_counted_and_flagged():
    cost = RunCost(CARD)
    cost.record("unheard-of", input_tokens=1000, output_tokens=1000)
    assert cost.total == Decimal("0")
    assert cost.unpriced == ("unheard-of",)


def test_a_fresh_run_costs_nothing():
    assert RunCost(CARD).total == Decimal("0")


def test_spend_is_broken_down_by_model():
    cost = RunCost(CARD)
    cost.record("small", input_tokens=1000, output_tokens=0)
    cost.record("small", input_tokens=1000, output_tokens=0)
    assert cost.by_model["small"] == Decimal("0.0010")


@pytest.mark.parametrize("budget,expected", [("0.01", False), ("0.001", True)])
def test_a_money_budget_can_be_exceeded(budget, expected):
    cost = RunCost(CARD, limit=Decimal(budget))
    cost.record("small", input_tokens=1000, output_tokens=1000)
    assert cost.exceeded is expected


def test_without_a_limit_nothing_is_ever_exceeded():
    cost = RunCost(CARD)
    cost.record("large", input_tokens=10_000_000, output_tokens=10_000_000)
    assert cost.exceeded is False
