"""Tokens, in money."""

from __future__ import annotations

from decimal import Decimal

from agent.src.analytics.priced import priced_usage

ROWS = [
    {"model": "gemini-3.8-flash", "input_tokens": 1000, "output_tokens": 500},
    {"model": "unrecorded", "input_tokens": 200, "output_tokens": 100},
]


def _pricer(known: dict[str, str]):
    """Stands in for the rate card."""

    def price(model: str, *, input_tokens: int, output_tokens: int):
        if model not in known:
            return {
                "cost": None,
                "currency": "USD",
                "rate_card_version": "v1",
                "unpriced": [model],
            }
        return {
            "cost": known[model],
            "currency": "USD",
            "rate_card_version": "v1",
            "unpriced": [],
        }

    return price


class TestPricingTheRows:
    def test_a_priced_model_gets_a_cost(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["rows"][0]["cost"] == "0.42"

    def test_the_other_columns_survive(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["rows"][0]["input_tokens"] == 1000

    def test_the_rate_card_that_priced_it_is_named(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["rate_card_version"] == "v1"

    def test_the_currency_is_stated(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["currency"] == "USD"


class TestAModelTheCardDoesNotPrice:
    def test_its_cost_is_absent_rather_than_zero(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["rows"][1]["cost"] is None

    def test_it_is_named_so_somebody_can_add_it(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert "unrecorded" in found["unpriced"]

    def test_the_total_says_it_is_incomplete(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["complete"] is False

    def test_the_total_is_still_given_as_far_as_it_goes(self):
        found = priced_usage(ROWS, price=_pricer({"gemini-3.8-flash": "0.42"}))
        assert found["total"] == "0.42"


class TestWhenEverythingIsPriced:
    def test_the_total_is_the_sum(self):
        found = priced_usage(
            ROWS, price=_pricer({"gemini-3.8-flash": "0.42", "unrecorded": "0.08"})
        )
        assert Decimal(found["total"]) == Decimal("0.50")

    def test_a_small_rate_is_not_rounded_away(self):
        tiny = [{"model": "a", "input_tokens": 1, "output_tokens": 0}]
        found = priced_usage(tiny, price=_pricer({"a": "0.000125"}))
        assert Decimal(found["total"]) == Decimal("0.000125")

    def test_and_it_says_so(self):
        found = priced_usage(
            ROWS, price=_pricer({"gemini-3.8-flash": "0.42", "unrecorded": "0.08"})
        )
        assert found["complete"] is True

    def test_nothing_is_unpriced(self):
        found = priced_usage(
            ROWS, price=_pricer({"gemini-3.8-flash": "0.42", "unrecorded": "0.08"})
        )
        assert found["unpriced"] == []


class TestWhenThereIsNoRateCard:
    def test_no_costs_are_invented(self):
        found = priced_usage(ROWS, price=_pricer({}))
        assert all(row["cost"] is None for row in found["rows"])

    def test_the_total_is_absent_rather_than_zero(self):
        found = priced_usage(ROWS, price=_pricer({}))
        assert found["total"] is None

    def test_and_it_is_not_called_complete(self):
        found = priced_usage(ROWS, price=_pricer({}))
        assert found["complete"] is False


class TestArithmetic:
    def test_money_is_added_exactly(self):
        rows = [
            {"model": "a", "input_tokens": 1, "output_tokens": 0},
            {"model": "b", "input_tokens": 1, "output_tokens": 0},
        ]
        found = priced_usage(rows, price=_pricer({"a": "0.1", "b": "0.2"}))
        assert Decimal(found["total"]) == Decimal("0.3")

    def test_nothing_to_price_is_not_an_error(self):
        found = priced_usage([], price=_pricer({"a": "1"}))
        assert found["rows"] == [] and found["total"] is None


class TestTheModelsEndpointPricesItsRows:
    """The breakdown already had the tokens; it never had the money."""

    @staticmethod
    async def _models(rows):
        from unittest.mock import AsyncMock, patch

        from agent.aegra import analytics_routes as ar
        from agent.src.analytics import queries

        with patch.object(queries, "by_model", new=AsyncMock(return_value=rows)):
            return await ar.analytics_models(days=7, _token="t")

    async def test_each_row_carries_a_cost_field(self):
        body = await self._models(
            [{"model": "x", "input_tokens": 10, "output_tokens": 5}]
        )
        assert "cost" in body["models"][0]

    async def test_the_rate_card_version_travels_with_the_figures(self):
        body = await self._models(
            [{"model": "x", "input_tokens": 10, "output_tokens": 5}]
        )
        assert "rate_card_version" in body

    async def test_a_model_with_no_price_is_named(self):
        body = await self._models(
            [{"model": "nothing-prices-this", "input_tokens": 10, "output_tokens": 5}]
        )
        assert body["unpriced"] == ["nothing-prices-this"]

    async def test_and_the_total_is_not_called_complete(self):
        body = await self._models(
            [{"model": "nothing-prices-this", "input_tokens": 10, "output_tokens": 5}]
        )
        assert body["complete"] is False

    async def test_the_rows_are_still_the_rows(self):
        body = await self._models(
            [{"model": "x", "runs": 3, "input_tokens": 10, "output_tokens": 5}]
        )
        assert body["models"][0]["runs"] == 3
