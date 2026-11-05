"""An unconnected integration must end the turn, not pause it."""

from __future__ import annotations

import pytest
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from agent.aegra.mcp_auth import NeedsAuthorization
from agent.aegra.mcp_tool_auth import _mcp_auth_message, wrap_mcp_tools_for_auth
from agent.src.settings import settings


class _Input(BaseModel):
    query: str = ""


def _tool_that_needs_auth() -> StructuredTool:
    async def _boom(query: str = "") -> str:
        raise NeedsAuthorization("dataverse", "http://localhost:8081/connect")

    return StructuredTool(
        name="dataverse_execute_sql",
        description="runs SQL",
        func=lambda query="": "",
        coroutine=_boom,
        args_schema=_Input,
    )


class TestTheRunIsNotPaused:
    def test_interrupting_is_off_by_default(self):
        assert settings.MCP_AUTH_INTERRUPT is False

    @pytest.mark.asyncio
    async def test_the_tool_returns_a_message_instead_of_interrupting(self):
        """`interrupt()` raises `GraphInterrupt` outside a running graph,"""
        wrapped = wrap_mcp_tools_for_auth([_tool_that_needs_auth()])[0]
        result = await wrapped.coroutine(query="select 1")
        assert "AUTH_REQUIRED mcp=dataverse" in str(result)


class TestTheModelIsToldToStop:
    def test_the_message_leaves_the_sentence_to_the_ui(self):
        """It used to hand the model that sentence to repeat."""
        msg = _mcp_auth_message(NeedsAuthorization("dataverse", "http://x"))
        assert settings.MCP_SETTINGS_PATH not in msg
        assert "dataverse" in msg

    def test_it_says_to_end_the_turn_and_not_retry(self):
        msg = _mcp_auth_message(NeedsAuthorization("dataverse", "http://x"))
        assert "End the turn now" in msg
        assert "Do not retry this tool" in msg

    def test_no_connect_button_is_promised(self):
        """The button went with the mid-chat flow; promising one sends"""
        msg = _mcp_auth_message(NeedsAuthorization("dataverse", "http://x"))
        assert "Connect button" not in msg

    def test_no_url_reaches_the_model(self):
        msg = _mcp_auth_message(
            NeedsAuthorization("dataverse", "http://localhost:8081/c")
        )
        assert "http" not in msg.replace("http://", "", 0) or "localhost" not in msg
