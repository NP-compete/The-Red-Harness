"""PII scrubbing that cannot be built must not quietly be absent."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.src.infrastructure.middleware import (
    PIIProtectionUnavailable,
    _build_custom_pii_middleware,
)


def test_nothing_is_built_when_pii_is_not_active():
    """No scrubber configured is not a failure — it is the default."""
    with patch("agent.src.pii.get_scrubber", return_value=None):
        assert _build_custom_pii_middleware() is None


def test_it_builds_when_a_scrubber_is_configured():
    from unittest.mock import MagicMock

    with patch("agent.src.pii.get_scrubber", return_value=MagicMock()):
        assert _build_custom_pii_middleware() is not None


def test_a_configured_scrubber_that_cannot_be_wrapped_refuses():
    """The deeper case: the import worked and the build did not."""
    from unittest.mock import MagicMock

    from agent.src.pii.middleware import PIIMiddlewareUnavailable

    with (
        patch("agent.src.pii.get_scrubber", return_value=MagicMock()),
        patch(
            "agent.src.pii.middleware.PIIMiddleware",
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(PIIMiddlewareUnavailable, match="unmasked"):
            _build_custom_pii_middleware()


def test_it_refuses_rather_than_running_unprotected():
    with patch(
        "agent.src.pii.middleware.build_pii_middleware",
        side_effect=ImportError("no presidio"),
    ):
        with pytest.raises(PIIProtectionUnavailable):
            _build_custom_pii_middleware()


def test_the_refusal_says_what_is_missing():
    with patch(
        "agent.src.pii.middleware.build_pii_middleware",
        side_effect=ImportError("no presidio"),
    ):
        with pytest.raises(PIIProtectionUnavailable, match="no presidio"):
            _build_custom_pii_middleware()


def test_the_refusal_says_how_to_run_without_it():
    """Turning the setting off is a decision; losing it silently is not."""
    with patch(
        "agent.src.pii.middleware.build_pii_middleware",
        side_effect=ImportError("no presidio"),
    ):
        with pytest.raises(PIIProtectionUnavailable, match="pii"):
            _build_custom_pii_middleware()
