"""Tying a result back to everything that produced it."""

from __future__ import annotations

import pytest

from agent.src.security.provenance_chain import Provenance, describe, verify


def provenance(**kwargs) -> Provenance:
    defaults = {
        "config_fingerprint": "cfg_7b19e4",
        "schema_version": 3,
        "resolver_version": "1",
        "model": "large",
        "rate_card_version": "2026-10",
        "image": "3.10.2",
    }
    defaults.update(kwargs)
    return Provenance(**defaults)


def test_a_complete_record_verifies():
    assert verify(provenance()).ok is True


def test_a_record_without_a_configuration_is_incomplete():
    assert verify(provenance(config_fingerprint="")).ok is False


def test_the_missing_part_is_named():
    assert "configuration" in verify(provenance(config_fingerprint="")).missing[0]


def test_several_missing_parts_are_all_named():
    result = verify(provenance(config_fingerprint="", model=""))
    assert len(result.missing) == 2


def test_a_record_without_an_image_cannot_be_reproduced():
    assert verify(provenance(image="")).ok is False


def test_a_rate_card_is_not_required_for_a_result_to_be_valid():
    assert verify(provenance(rate_card_version="")).ok is True


def test_a_rate_card_absence_is_still_noted():
    assert verify(provenance(rate_card_version="")).notes != ()


def test_a_record_renders_for_a_person():
    rendered = describe(provenance())
    assert "cfg_7b19e4" in rendered and "3.10.2" in rendered


def test_two_identical_records_describe_identically():
    assert describe(provenance()) == describe(provenance())


def test_a_different_configuration_describes_differently():
    assert describe(provenance()) != describe(
        provenance(config_fingerprint="cfg_other")
    )


@pytest.mark.parametrize("version", [0, -1])
def test_a_nonsense_schema_version_is_refused(version):
    with pytest.raises(ValueError):
        provenance(schema_version=version)
