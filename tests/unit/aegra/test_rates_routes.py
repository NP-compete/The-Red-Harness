"""The prices a deployment charges its model calls at."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.aegra import rates_routes

CARD = """
version: 2026-10
rates:
  gemini-3.8-flash:
    input_per_1k: "0.00015"
    output_per_1k: "0.0006"
"""


@pytest.fixture
def card_at(tmp_path, monkeypatch):
    def write(text: str | None) -> Path:
        path = tmp_path / "rates.yaml"
        if text is not None:
            path.write_text(text)
        monkeypatch.setattr(rates_routes, "_card_path", lambda: path)
        rates_routes.rate_card.cache_clear()
        return path

    return write


@pytest.mark.asyncio
async def test_says_which_version_of_the_prices_is_in_force(card_at):
    card_at(CARD)
    assert (await rates_routes.list_rates())["version"] == "2026-10"


@pytest.mark.asyncio
async def test_lists_a_model_and_what_it_costs(card_at):
    card_at(CARD)
    rates = (await rates_routes.list_rates())["rates"]
    assert rates == [
        {
            "model": "gemini-3.8-flash",
            "input_per_1k": "0.00015",
            "output_per_1k": "0.0006",
        }
    ]


@pytest.mark.asyncio
async def test_a_deployment_with_no_prices_says_so_rather_than_saying_free(card_at):
    card_at(None)
    found = await rates_routes.list_rates()
    assert found["rates"] == [] and found["version"] == "none"


@pytest.mark.asyncio
async def test_says_where_prices_would_be_read_from(card_at):
    """Otherwise "no prices" is a dead end rather than something to fix."""
    path = card_at(None)
    assert (await rates_routes.list_rates())["source"] == str(path)


@pytest.mark.asyncio
async def test_an_unreadable_price_list_is_not_served_as_no_prices(card_at):
    card_at("rates: {}")
    found = await rates_routes.list_rates()
    assert found["problem"] and found["rates"] == []


@pytest.mark.asyncio
async def test_the_prices_are_read_once_rather_than_per_request(card_at):
    path = card_at(CARD)
    await rates_routes.list_rates()
    path.write_text(CARD.replace("2026-10", "2026-11"))
    assert (await rates_routes.list_rates())["version"] == "2026-10"


@pytest.mark.asyncio
async def test_prices_a_run_at_the_rate_that_applied(card_at):
    card_at(CARD)
    priced = rates_routes.price_tokens(
        "gemini-3.8-flash", input_tokens=1000, output_tokens=1000
    )
    assert priced["cost"] == "0.00075"


@pytest.mark.asyncio
async def test_says_which_version_priced_it(card_at):
    card_at(CARD)
    priced = rates_routes.price_tokens(
        "gemini-3.8-flash", input_tokens=10, output_tokens=0
    )
    assert priced["rate_card_version"] == "2026-10"


@pytest.mark.asyncio
async def test_a_model_with_no_price_is_unpriced_rather_than_free(card_at):
    card_at(CARD)
    priced = rates_routes.price_tokens(
        "some-other-model", input_tokens=1000, output_tokens=1000
    )
    assert priced["cost"] is None and priced["unpriced"] == ["some-other-model"]


@pytest.mark.asyncio
async def test_a_run_with_no_model_recorded_is_not_priced(card_at):
    card_at(CARD)
    assert (
        rates_routes.price_tokens("", input_tokens=1000, output_tokens=0)["cost"]
        is None
    )


@pytest.mark.asyncio
async def test_prices_what_a_thread_has_used(card_at, monkeypatch):
    """A token total nobody can convert to money is a token total."""
    card_at(CARD)
    monkeypatch.setattr(rates_routes, "orchestrator_model", lambda: "gemini-3.8-flash")
    costed = rates_routes.cost_of_thread({"input_tokens": 2000, "output_tokens": 1000})
    assert costed["cost"] == "0.0009"


@pytest.mark.asyncio
async def test_a_thread_priced_at_the_model_that_answered_it(card_at, monkeypatch):
    card_at(CARD)
    monkeypatch.setattr(rates_routes, "orchestrator_model", lambda: "another-model")
    costed = rates_routes.cost_of_thread({"input_tokens": 10, "output_tokens": 10})
    assert costed["unpriced"] == ["another-model"]


@pytest.mark.asyncio
async def test_a_thread_with_no_counts_yet_costs_nothing_rather_than_failing(
    card_at, monkeypatch
):
    card_at(CARD)
    monkeypatch.setattr(rates_routes, "orchestrator_model", lambda: "gemini-3.8-flash")
    assert rates_routes.cost_of_thread({})["cost"] == "0"


@pytest.mark.asyncio
async def test_prices_counts_a_caller_has_of_its_own(card_at, monkeypatch):
    """Usage tracking can be off, and the turns on screen still cost something."""
    card_at(CARD)
    monkeypatch.setattr(rates_routes, "orchestrator_model", lambda: "gemini-3.8-flash")
    assert (await rates_routes.price(input_tokens=2000, output_tokens=1000))[
        "cost"
    ] == "0.0009"


@pytest.mark.asyncio
async def test_prices_nothing_at_all_as_nothing(card_at, monkeypatch):
    card_at(CARD)
    monkeypatch.setattr(rates_routes, "orchestrator_model", lambda: "gemini-3.8-flash")
    assert (await rates_routes.price(input_tokens=0, output_tokens=0))["cost"] == "0"


@pytest.mark.asyncio
async def test_negative_counts_are_refused_rather_than_credited(card_at, monkeypatch):
    from fastapi import HTTPException

    card_at(CARD)
    with pytest.raises(HTTPException) as exc:
        await rates_routes.price(input_tokens=-1, output_tokens=0)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_says_what_a_run_may_spend(card_at, monkeypatch):
    """A ceiling nobody is told about is one they discover by hitting it."""
    card_at(CARD)
    from agent.src.agent.config.middleware import SpendLimitConfig

    monkeypatch.setattr(
        rates_routes, "_spend_limit", lambda: SpendLimitConfig(refuse_at="0.05")
    )
    assert (await rates_routes.list_rates())["run_limit"] == "0.05"


@pytest.mark.asyncio
async def test_a_deployment_with_no_ceiling_says_so(card_at, monkeypatch):
    card_at(CARD)
    from agent.src.agent.config.middleware import SpendLimitConfig

    monkeypatch.setattr(rates_routes, "_spend_limit", lambda: SpendLimitConfig())
    assert (await rates_routes.list_rates())["run_limit"] == ""


@pytest.mark.asyncio
async def test_the_warning_threshold_is_reported_too(card_at, monkeypatch):
    card_at(CARD)
    from agent.src.agent.config.middleware import SpendLimitConfig

    monkeypatch.setattr(
        rates_routes,
        "_spend_limit",
        lambda: SpendLimitConfig(warn_at="0.01", refuse_at="0.05"),
    )
    assert (await rates_routes.list_rates())["run_warn_at"] == "0.01"


@pytest.mark.asyncio
async def test_an_unreadable_ceiling_is_reported_as_none_rather_than_crashing(
    card_at, monkeypatch
):
    card_at(CARD)
    from agent.src.agent.config.middleware import SpendLimitConfig

    monkeypatch.setattr(
        rates_routes, "_spend_limit", lambda: SpendLimitConfig(refuse_at="tuppence")
    )
    assert (await rates_routes.list_rates())["run_limit"] == ""
