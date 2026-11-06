"""What the model is told when an integration cannot be reached."""

from __future__ import annotations

from types import SimpleNamespace

from agent.aegra.mcp_tool_auth import _mcp_auth_message
from agent.src.settings import settings


def message(name: str = "gitlab", reason: str = "not_connected") -> str:
    return _mcp_auth_message(SimpleNamespace(mcp_name=name, reason=reason))


def test_the_marker_still_names_the_integration():
    """The row the reader sees is built from this."""
    assert "mcp=gitlab" in message()


def test_the_marker_still_carries_the_reason():
    assert "reason=not_connected" in message()


def test_the_model_is_told_to_stop():
    assert "End the turn" in message()


def test_the_model_is_not_told_to_write_the_instruction_again():
    assert settings.MCP_SETTINGS_PATH not in message()


def test_the_model_is_not_handed_a_sentence_to_copy():
    assert "Connect it in" not in message()


def test_the_model_is_still_told_what_to_say():
    """Saying nothing at all reads as the agent ignoring the question."""
    assert "gitlab" in message().lower()


def test_the_model_is_still_kept_away_from_links():
    assert "URL" in message()


def test_the_model_is_still_told_not_to_try_again():
    assert "Do not retry" in message()
