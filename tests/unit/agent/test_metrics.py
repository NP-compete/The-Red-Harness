"""Recording what happened without flooding the metrics with labels."""

from __future__ import annotations

import pytest

from agent.src.agent.metrics import Measurement, prepare


def measurement(**kwargs) -> Measurement:
    defaults = {
        "name": "run.duration",
        "value": 1.5,
        "labels": {"agent": "triage", "outcome": "ok"},
    }
    defaults.update(kwargs)
    return Measurement(**defaults)


def test_an_ordinary_measurement_is_kept_as_it_is():
    prepared = prepare([measurement()], known_labels=("agent", "outcome"))
    assert prepared.measurements[0].labels == {"agent": "triage", "outcome": "ok"}


def test_a_label_nobody_declared_is_dropped():
    odd = measurement(labels={"agent": "triage", "run_id": "r-12345"})
    prepared = prepare([odd], known_labels=("agent",))
    assert prepared.measurements[0].labels == {"agent": "triage"}


def test_a_dropped_label_is_reported_rather_than_silently_lost():
    odd = measurement(labels={"agent": "triage", "run_id": "r-12345"})
    assert prepare([odd], known_labels=("agent",)).dropped_labels == ("run_id",)


def test_a_label_with_too_many_values_is_collapsed():
    many = [
        measurement(labels={"agent": f"agent-{n}", "outcome": "ok"}) for n in range(60)
    ]
    prepared = prepare(many, known_labels=("agent", "outcome"), max_values=50)
    assert prepared.measurements[0].labels["agent"] == "other"


def test_collapsing_a_label_is_reported():
    many = [measurement(labels={"agent": f"agent-{n}"}) for n in range(60)]
    prepared = prepare(many, known_labels=("agent",), max_values=50)
    assert prepared.collapsed_labels == ("agent",)


def test_a_label_within_its_limit_is_left_alone():
    few = [measurement(labels={"agent": f"agent-{n}"}) for n in range(5)]
    prepared = prepare(few, known_labels=("agent",), max_values=50)
    assert prepared.measurements[0].labels["agent"] == "agent-0"


def test_the_number_of_series_is_reported():
    mixed = [
        measurement(labels={"agent": "a", "outcome": "ok"}),
        measurement(labels={"agent": "b", "outcome": "ok"}),
        measurement(labels={"agent": "a", "outcome": "ok"}),
    ]
    assert prepare(mixed, known_labels=("agent", "outcome")).series == 2


def test_a_measurement_with_no_labels_is_one_series():
    assert prepare([measurement(labels={})], known_labels=()).series == 1


def test_a_value_that_is_not_a_number_is_refused():
    with pytest.raises(ValueError):
        Measurement(name="x", value=float("nan"), labels={})


def test_an_infinite_value_is_refused():
    with pytest.raises(ValueError):
        Measurement(name="x", value=float("inf"), labels={})


def test_a_measurement_without_a_name_is_refused():
    with pytest.raises(ValueError):
        Measurement(name="  ", value=1.0, labels={})


def test_a_label_value_that_looks_like_free_text_is_refused():
    with pytest.raises(ValueError):
        Measurement(name="x", value=1.0, labels={"note": "a whole sentence of detail"})


def test_the_total_number_of_series_is_capped():
    many = [
        measurement(labels={"agent": f"a{n}", "outcome": f"o{n}"}) for n in range(40)
    ]
    prepared = prepare(many, known_labels=("agent", "outcome"), max_series=10)
    assert prepared.series <= 10


def test_hitting_the_series_cap_is_reported():
    many = [
        measurement(labels={"agent": f"a{n}", "outcome": f"o{n}"}) for n in range(40)
    ]
    assert (
        prepare(many, known_labels=("agent", "outcome"), max_series=10).capped is True
    )


def test_staying_under_the_cap_is_not_reported_as_capped():
    assert prepare([measurement()], known_labels=("agent", "outcome")).capped is False


def test_preparing_nothing_is_refused():
    with pytest.raises(ValueError):
        prepare([], known_labels=("agent",))
