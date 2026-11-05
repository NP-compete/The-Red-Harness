"""Asking what a month cost, per payer."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

LEDGER = {
    "platform": {"amount": Decimal("412.50"), "runs": 318},
    "alice": {"amount": Decimal("18.25"), "runs": 27},
}


@pytest.fixture
def client() -> TestClient:
    from agent.aegra.http_app import app

    return TestClient(app)


def _asked(client, *, ledger=None, month="2026-03"):
    async def _charges(when, **kwargs):
        return LEDGER if ledger is None else ledger

    with (
        patch("agent.aegra.costs_routes._charges_in", side_effect=_charges),
        patch("agent.aegra.costs_routes._who", return_value="alice"),
    ):
        return client.get(f"/costs/chargeback?month={month}")


class TestWhatComesBack:
    def test_it_answers(self, client):
        assert _asked(client).status_code == 200

    def test_it_lists_a_row_per_payer(self, client):
        assert len(_asked(client).json()["rows"]) == 2

    def test_a_row_names_the_payer(self, client):
        payers = {row["payer"] for row in _asked(client).json()["rows"]}
        assert payers == {"platform", "alice"}

    def test_a_row_carries_the_money(self, client):
        found = next(
            row for row in _asked(client).json()["rows"] if row["payer"] == "platform"
        )
        assert found["amount"] == "412.50"

    def test_money_is_a_string(self, client):
        found = _asked(client).json()["rows"][0]
        assert isinstance(found["amount"], str)

    def test_a_row_carries_the_run_count(self, client):
        found = next(
            row for row in _asked(client).json()["rows"] if row["payer"] == "platform"
        )
        assert found["runs"] == 318

    def test_the_biggest_payer_comes_first(self, client):
        assert _asked(client).json()["rows"][0]["payer"] == "platform"

    def test_it_says_which_month(self, client):
        assert _asked(client).json()["month"] == "2026-03"

    def test_it_says_the_currency(self, client):
        assert _asked(client).json()["currency"]

    def test_it_says_which_prices_applied(self, client):
        assert "rate_card_version" in _asked(client).json()

    def test_it_totals_the_month(self, client):
        assert _asked(client).json()["total"] == "430.75"


class TestAMonthWithNothingInIt:
    def test_it_still_answers(self, client):
        assert _asked(client, ledger={}).status_code == 200

    def test_it_returns_no_rows_rather_than_an_error(self, client):
        assert _asked(client, ledger={}).json()["rows"] == []

    def test_the_total_is_zero(self, client):
        assert _asked(client, ledger={}).json()["total"] == "0.00"


class TestAskingForTheWrongThing:
    def test_a_month_that_is_not_a_month_is_refused(self, client):
        assert _asked(client, month="March").status_code == 422

    def test_a_day_is_refused(self, client):
        assert _asked(client, month="2026-03-04").status_code == 422

    def test_no_month_at_all_means_this_one(self, client):
        async def _charges(when, **kwargs):
            return {}

        with (
            patch("agent.aegra.costs_routes._charges_in", side_effect=_charges),
            patch("agent.aegra.costs_routes._who", return_value="alice"),
        ):
            found = client.get("/costs/chargeback")

        assert len(found.json()["month"]) == len("2026-03")
