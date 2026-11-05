"""Reading prices from configuration rather than hard-coding them."""

from __future__ import annotations

import pytest
import yaml

from agent.src.security.cost import RateCard
from agent.src.security.rate_card_config import load_rate_card

CARD_YAML = """
version: "2026-10"
rates:
  small:
    input_per_1k: "0.0005"
    output_per_1k: "0.0015"
  large:
    input_per_1k: "0.01"
    output_per_1k: "0.03"
"""


def write(tmp_path, text, name="rates.yaml"):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_a_card_loads_from_a_file(tmp_path):
    card = load_rate_card(write(tmp_path, CARD_YAML))
    assert isinstance(card, RateCard)
    assert card.version == "2026-10"


def test_the_rates_are_usable(tmp_path):
    card = load_rate_card(write(tmp_path, CARD_YAML))
    assert card.price("small", input_tokens=1000, output_tokens=0) is not None


def test_a_missing_file_prices_nothing_rather_than_guessing(tmp_path):
    card = load_rate_card(tmp_path / "absent.yaml")
    assert card.price("small", input_tokens=1000, output_tokens=0) is None


def test_a_missing_file_is_marked_as_having_no_prices(tmp_path):
    assert load_rate_card(tmp_path / "absent.yaml").version == "none"


def test_a_card_without_a_version_is_refused(tmp_path):
    with pytest.raises(ValueError):
        load_rate_card(write(tmp_path, yaml.safe_dump({"rates": {}})))


def test_a_rate_missing_a_price_is_refused(tmp_path):
    bad = yaml.safe_dump({"version": "x", "rates": {"small": {"input_per_1k": "0.1"}}})
    with pytest.raises(ValueError):
        load_rate_card(write(tmp_path, bad))


def test_a_negative_price_is_refused(tmp_path):
    bad = yaml.safe_dump(
        {
            "version": "x",
            "rates": {"small": {"input_per_1k": "-1", "output_per_1k": "0.1"}},
        }
    )
    with pytest.raises(ValueError):
        load_rate_card(write(tmp_path, bad))


def test_an_unparseable_file_is_refused_rather_than_silently_empty(tmp_path):
    with pytest.raises(ValueError):
        load_rate_card(write(tmp_path, "this: [is: broken"))


def test_a_card_with_no_rates_loads_but_prices_nothing(tmp_path):
    card = load_rate_card(
        write(tmp_path, yaml.safe_dump({"version": "empty", "rates": {}}))
    )
    assert card.version == "empty"
    assert card.price("small", input_tokens=1, output_tokens=1) is None
