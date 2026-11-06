"""An unreachable MCP server is taken out of service (REL-3)."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

from agent.aegra import mcp, mcp_host


@pytest.fixture
def server(monkeypatch):
    """A configured server whose connection does what the test says."""

    def set_up(fail_with: Exception | None):
        monkeypatch.setattr(
            mcp_host, "_get_enabled_server", lambda name: {"url": "http://nowhere/mcp"}
        )

        async def bearer(*_args, **_kwargs):
            return "token"

        monkeypatch.setattr(mcp_host, "_resolve_bearer", bearer)
        monkeypatch.setattr(mcp_host, "_build_server_config", lambda *a, **k: {})
        monkeypatch.setattr(
            mcp_host, "ensure_mcp_apps_capability_advertised", lambda: None
        )

        class FakeClient:
            def __init__(self, *_a, **_k): ...

            @asynccontextmanager
            async def session(self, _name):
                if fail_with is not None:
                    raise fail_with
                yield "a session"

        monkeypatch.setattr(mcp_host, "MultiServerMCPClient", FakeClient)

    return set_up


@pytest.fixture(autouse=True)
def a_fresh_breaker(monkeypatch):
    monkeypatch.setattr(mcp, "_mcp_breakers", {})


async def _open(name: str = "dead"):
    async with mcp_host.mcp_session(name, user_id="ada", sso_token="t") as session:
        return session


class TestItStopsTryingAfterFiveFailures:
    @pytest.mark.asyncio
    async def test_the_sixth_call_is_refused_without_connecting(self, server):
        server(fail_with=ConnectionError("Connect call failed"))
        for _ in range(5):
            with pytest.raises(ConnectionError):
                await _open()

        server(fail_with=None)
        with pytest.raises(HTTPException) as refused:
            await _open()
        assert refused.value.status_code == 503
        assert "dead" in refused.value.detail
        assert "Nothing was sent to it" in refused.value.detail

    @pytest.mark.asyncio
    async def test_four_failures_are_not_enough(self, server):
        """A breaker that opens too early is its own outage."""
        server(fail_with=ConnectionError("Connect call failed"))
        for _ in range(4):
            with pytest.raises(ConnectionError):
                await _open()
        server(fail_with=None)
        assert await _open() == "a session"


class TestWhatDoesNotCount:
    @pytest.mark.asyncio
    async def test_an_auth_failure_does_not_open_it(self, server):
        """The caller is wrong, not the server."""
        server(fail_with=PermissionError("401 Unauthorized"))
        for _ in range(8):
            with pytest.raises(PermissionError):
                await _open()
        server(fail_with=None)
        assert await _open() == "a session"

    @pytest.mark.asyncio
    async def test_a_breaker_is_per_server(self, server):
        server(fail_with=ConnectionError("Connect call failed"))
        for _ in range(5):
            with pytest.raises(ConnectionError):
                await _open("dead")
        server(fail_with=None)
        assert await _open("alive") == "a session"
