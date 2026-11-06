"""Answers whether the calling identity holds the credential a tool needs."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, Protocol

from agent.src.security.resolver import Identity, ToolCall


class Credentials(Protocol):
    """Answers whether a user has a usable token for an MCP server."""

    async def has_valid_token(
        self,
        user_id: str,
        mcp_name: str,
        server_cfg: dict[str, Any],
        *,
        verify: bool = False,
    ) -> bool:
        """Whether `user_id` holds a usable token for `mcp_name`."""
        ...


class CredentialAuthoritySource:
    """Authority drawn from whether the caller holds the server's credential."""

    def __init__(
        self, credentials: Credentials, servers: dict[str, dict[str, Any]]
    ) -> None:
        """Bind to a credential store and the known servers."""
        self._credentials = credentials
        self._servers = servers

    async def aholds(self, identity: Identity, call: ToolCall) -> bool | None:
        """Whether `identity` holds authority for `call`, awaiting the store."""
        prepared = self._prepare(identity, call)
        if not isinstance(prepared, tuple):
            return prepared
        subject, server, server_cfg = prepared
        try:
            return await self._credentials.has_valid_token(
                subject, server, server_cfg, verify=True
            )
        except Exception:
            return None

    def _prepare(
        self, identity: Identity, call: ToolCall
    ) -> bool | tuple[str, str, dict[str, Any]]:
        """The subject, server and config to check, or a settled answer."""
        if not call.server:
            return True
        server_cfg = self._servers.get(call.server)
        if server_cfg is None:
            return False
        return (identity.delegated_by or identity.subject, call.server, server_cfg)

    def holds(self, identity: Identity, call: ToolCall) -> bool | None:
        """Whether `identity` holds authority for `call`."""
        if not call.server:
            return True

        server_cfg = self._servers.get(call.server)
        if server_cfg is None:
            return False

        subject = identity.delegated_by or identity.subject

        try:
            return _run(
                self._credentials.has_valid_token(
                    subject, call.server, server_cfg, verify=True
                )
            )
        except Exception:
            return None


def _run(coro: Coroutine[Any, Any, bool]) -> bool:
    """Run `coro` to completion, refusing to block a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("holds() must not be called from a running event loop")
