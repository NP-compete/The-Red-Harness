"""Quality checks, and whether anybody actually runs them."""

from __future__ import annotations

import pytest

from agent.src.evals.registry import Check, CheckRegistry


def checks() -> list[Check]:
    return [
        Check(name="injection-resistance", group="safety", decides="whether to ship"),
        Check(name="citation-grounding", group="accuracy", decides="whether to ship"),
        Check(name="scope-leakage", group="privacy", decides="whether to ship"),
    ]


def registry(*, extra: list[Check] | None = None) -> CheckRegistry:
    return CheckRegistry(checks() + (extra or []))


def test_checks_are_listed_by_group():
    assert set(registry().groups()) == {"safety", "accuracy", "privacy"}


def test_a_group_lists_its_checks():
    assert [c.name for c in registry().in_group("safety")] == ["injection-resistance"]


def test_a_check_must_say_what_decision_it_informs():
    with pytest.raises(ValueError):
        Check(name="vague", group="safety", decides="")


def test_names_are_unique():
    with pytest.raises(ValueError):
        CheckRegistry(
            checks() + [Check(name="scope-leakage", group="privacy", decides="x")]
        )


def test_a_fresh_registry_has_run_nothing():
    assert registry().usage()["scope-leakage"] == 0


def test_running_a_check_is_counted():
    reg = registry()
    reg.record_run("scope-leakage")
    reg.record_run("scope-leakage")
    assert reg.usage()["scope-leakage"] == 2


def test_recording_an_unknown_check_is_refused():
    with pytest.raises(KeyError):
        registry().record_run("not-a-check")


def test_checks_nobody_runs_are_named_for_pruning():
    reg = registry()
    reg.record_run("scope-leakage")
    assert reg.unused() == ("citation-grounding", "injection-resistance")


def test_nothing_is_pruned_once_everything_has_run():
    reg = registry()
    for check in checks():
        reg.record_run(check.name)
    assert reg.unused() == ()


def test_pruning_is_advice_rather_than_deletion():
    reg = registry()
    reg.unused()
    assert len(reg.groups()) == 3
