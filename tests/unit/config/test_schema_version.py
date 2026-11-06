"""Whether a configuration tree can be loaded by this build."""

from __future__ import annotations

from agent.src.agent.config.schema_version import (
    CURRENT,
    OLDEST_SUPPORTED,
    Supported,
    TooNew,
    TooOld,
    check_schema_version,
)


def test_the_current_version_loads():
    assert isinstance(check_schema_version(CURRENT), Supported)


def test_the_previous_version_still_loads():
    assert isinstance(check_schema_version(CURRENT - 1), Supported)


def test_an_older_version_is_refused():
    assert isinstance(check_schema_version(OLDEST_SUPPORTED - 1), TooOld)


def test_a_refusal_for_an_old_tree_names_the_migration():
    result = check_schema_version(OLDEST_SUPPORTED - 1)
    assert str(OLDEST_SUPPORTED) in result.message
    assert "migrat" in result.message.lower()


def test_a_newer_version_is_refused():
    assert isinstance(check_schema_version(CURRENT + 1), TooNew)


def test_a_refusal_for_a_new_tree_says_to_upgrade():
    assert "upgrade" in check_schema_version(CURRENT + 1).message.lower()


def test_a_tree_without_a_version_is_treated_as_the_oldest_supported():
    result = check_schema_version(None)
    assert isinstance(result, Supported)
    assert result.version == OLDEST_SUPPORTED


def test_the_version_in_use_is_reported():
    assert check_schema_version(CURRENT).version == CURRENT


def test_a_deprecated_but_supported_tree_is_flagged():
    assert check_schema_version(OLDEST_SUPPORTED).deprecated is True


def test_the_current_tree_is_not_flagged():
    assert check_schema_version(CURRENT).deprecated is False
