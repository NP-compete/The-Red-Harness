"""What model calls are priced at, and what a run therefore cost."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from agent.src.security.cost import RateCard, RunCost
from agent.src.security.rate_card_config import NO_PRICES, load_rate_card
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/rates", tags=["rates"])


def _card_path() -> Path:
    """Where the rate card is read from."""
    return Path(settings.RATE_CARD_PATH)


@lru_cache(maxsize=1)
def rate_card() -> tuple[RateCard, str]:
    """The prices in force, and why there are none when there are none."""
    path = _card_path()
    try:
        return load_rate_card(path), ""
    except ValueError as error:
        logger.error("Model prices at %s could not be read: %s", path, error)
        return NO_PRICES, str(error)


def _spend_limit() -> Any:
    """What a single run may spend here, per configuration."""
    from agent.src.agent.config import agent_config

    return agent_config.get_middleware_config().defaults.spend_limit


def _amount(read: Any) -> str:
    """An amount as configured, or nothing when it cannot be read."""
    try:
        value = read()
    except ValueError:
        return ""
    return format(value, "f") if value is not None else ""


class RateOut(BaseModel):
    """One model's prices."""

    model_config = {"extra": "allow", "protected_namespaces": ()}

    model: str = ""


class RateCardOut(BaseModel):
    """The rate card in force, with its limits and version."""

    model_config = {"extra": "allow"}

    run_limit: str = ""
    run_warn_at: str = ""
    version: str = ""
    currency: str = ""
    source: str = ""
    problem: str = ""
    rates: list[RateOut] = []


class PriceOut(BaseModel):
    """What a call would cost, and which card priced it."""

    cost: str | None = None
    currency: str = ""
    rate_card_version: str = ""
    unpriced: list[str] = []


@router.get("", responses={200: {"model": RateCardOut}})
async def list_rates() -> dict[str, Any]:
    """Every priced model, so a figure in money can be checked."""
    card, problem = rate_card()
    limit = _spend_limit()
    return {
        "run_limit": _amount(limit.ceiling),
        "run_warn_at": _amount(limit.warning),
        "version": card.version,
        "currency": settings.RATE_CARD_CURRENCY,
        "source": str(_card_path()),
        "problem": problem,
        "rates": [
            {
                "model": model,
                "input_per_1k": rate.input_per_1k,
                "output_per_1k": rate.output_per_1k,
            }
            for model, rate in sorted(card.rates.items())
        ],
    }


def price_tokens(
    model: str, *, input_tokens: int, output_tokens: int
) -> dict[str, Any]:
    """What those tokens cost, or nothing at all when it cannot be said."""
    card, _problem = rate_card()
    run = RunCost(card)
    if model:
        run.record(model, input_tokens=input_tokens, output_tokens=output_tokens)

    priced = not run.unpriced and bool(model) and bool(card.rates)
    return {
        "cost": _plain(run.total) if priced else None,
        "currency": settings.RATE_CARD_CURRENCY,
        "rate_card_version": card.version,
        "unpriced": list(run.unpriced),
    }


@router.get("/price", responses={200: {"model": PriceOut}})
async def price(input_tokens: int = 0, output_tokens: int = 0) -> dict[str, Any]:
    """What these counts cost, for a caller holding its own tally."""
    from fastapi import HTTPException

    if input_tokens < 0 or output_tokens < 0:
        raise HTTPException(status_code=422, detail="Token counts cannot be negative")

    return price_tokens(
        orchestrator_model(), input_tokens=input_tokens, output_tokens=output_tokens
    )


def orchestrator_model() -> str:
    """The model a conversation is answered by, per configuration."""
    from agent.src.agent.config import agent_config

    try:
        model = agent_config.get_orchestrator_config().get("model")
    except Exception:
        logger.debug("Could not read the configured model", exc_info=True)
        return ""
    return str(model.get("name") or "") if isinstance(model, dict) else str(model or "")


def cost_of_thread(usage: dict[str, Any]) -> dict[str, Any]:
    """What a conversation's tokens come to in money."""
    return price_tokens(
        orchestrator_model(),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )


def _plain(amount: Decimal) -> str:
    """A fixed-point string: money through a float is money lost."""
    return format(amount.normalize(), "f")
