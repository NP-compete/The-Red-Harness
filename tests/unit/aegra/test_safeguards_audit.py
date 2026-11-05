"""Whether what the agent does is being recorded."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.aegra import skill_routes


@pytest.mark.asyncio
async def test_reports_that_actions_are_recorded():
    with patch("agent.src.audit.config.settings.PLATFORM_AUDIT_ENABLED", True):
        found = await skill_routes.list_safeguards()
    assert found["audit"]["enabled"] is True


@pytest.mark.asyncio
async def test_reports_that_they_are_not():
    """A safeguards page that omits this reads as if it were on."""
    with patch("agent.src.audit.config.settings.PLATFORM_AUDIT_ENABLED", False):
        found = await skill_routes.list_safeguards()
    assert found["audit"]["enabled"] is False


@pytest.mark.asyncio
async def test_still_reports_the_other_safeguards():
    with patch("agent.src.audit.config.settings.PLATFORM_AUDIT_ENABLED", True):
        found = await skill_routes.list_safeguards()
    assert "pii" in found
    assert "guardrail" in found
    assert "token_budget" in found
