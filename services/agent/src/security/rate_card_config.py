"""Loading model prices from configuration."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from agent.src.security.cost import ModelRate, RateCard

NO_PRICES = RateCard(version="none", rates={})


def load_rate_card(path: Path) -> RateCard:
    """Read the rate card at `path`, or no prices if it is absent."""
    if not path.is_file():
        return NO_PRICES

    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as error:
        raise ValueError(f"{path} is not readable as a price list: {error}") from error

    version = str(raw.get("version", "")).strip()
    if not version:
        raise ValueError(f"{path} must say which version of the prices it holds")

    rates: dict[str, ModelRate] = {}
    for model, prices in (raw.get("rates") or {}).items():
        rates[model] = _rate(path, model, prices or {})

    return RateCard(version=version, rates=rates)


def _rate(path: Path, model: str, prices: dict) -> ModelRate:
    """One model's rate, rejecting a missing or negative price."""
    for field in ("input_per_1k", "output_per_1k"):
        if field not in prices:
            raise ValueError(f"{path}: '{model}' is missing {field}")
        try:
            if Decimal(str(prices[field])) < 0:
                raise ValueError(f"{path}: '{model}' has a negative {field}")
        except InvalidOperation as error:
            raise ValueError(f"{path}: '{model}' has an unreadable {field}") from error

    return ModelRate(
        input_per_1k=str(prices["input_per_1k"]),
        output_per_1k=str(prices["output_per_1k"]),
    )
