"""What the agent is connected to, and what it knows how to do."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class InventoryFailed(RuntimeError):
    """The agent would not, or could not, answer."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...

    def post(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        ...

    def delete(self, path: str) -> tuple[int, Any]:
        """DELETE `path` and return the status and decoded body."""
        ...


@dataclass(frozen=True)
class Server:
    """One MCP server as the agent reports it."""

    name: str
    display_name: str
    enabled: bool
    auth_mode: str
    connected: bool | None
    account: str


@dataclass(frozen=True)
class Skill:
    """One skill as the agent reports it."""

    name: str
    description: str


def list_servers(*, transport: Transport) -> list[Server]:
    """Every MCP server the agent knows about."""
    status, payload = transport.get("/mcp/servers")
    if status != 200:
        raise InventoryFailed(f"Could not list servers ({status}): {_why(payload)}")

    rows = _rows_in(payload, "servers")
    if rows is None:
        raise InventoryFailed("The agent answered with something that is not a list")

    linked = _connections(transport)

    return [
        Server(
            name=str(row.get("name", "")),
            display_name=str(row.get("display_name") or row.get("name") or ""),
            enabled=bool(row.get("enabled", False)),
            auth_mode=str(row.get("auth_mode") or ""),
            connected=None
            if linked is None
            else bool((linked.get(str(row.get("name", ""))) or {}).get("connected")),
            account=str(
                ((linked or {}).get(str(row.get("name", ""))) or {}).get("account")
                or ""
            ),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _connections(transport: Transport) -> dict[str, dict] | None:
    """The OAuth connections, keyed by server, or `None` if unreadable."""
    status, payload = transport.get("/mcp/oauth/connections")
    if status != 200:
        return None
    rows = _rows_in(payload, "connections")
    if rows is None:
        return None
    return {str(row.get("mcp_name", "")): row for row in rows if isinstance(row, dict)}


def list_skills(*, transport: Transport) -> list[Skill]:
    """Every skill the agent knows about."""
    status, payload = transport.get("/skills")
    if status != 200:
        raise InventoryFailed(f"Could not list skills ({status}): {_why(payload)}")

    rows = _rows_in(payload, "skills")
    if rows is None:
        raise InventoryFailed("The agent answered with something that is not a list")

    return [
        Skill(
            name=str(row.get("name", "")),
            description=str(row.get("description") or ""),
        )
        for row in rows
        if isinstance(row, dict)
    ]


def _rows_in(payload: Any, key: str) -> list | None:
    """The rows, wrapped or bare."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        rows: list[Any] = payload[key]
        return rows
    return None


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("message") or payload)
    return str(payload)


@dataclass(frozen=True)
class Authorization:
    """Where a person has to go to finish connecting."""

    mcp_name: str
    authorize_url: str


def begin_connect(name: str, *, transport: Transport) -> Authorization:
    """Start an OAuth flow and return the URL to visit."""
    status, payload = transport.post(f"/mcp/{name}/connect", {})
    if status != 200:
        raise InventoryFailed(f"Could not start {name} ({status}): {_why(payload)}")
    url = (payload or {}).get("authorize_url") if isinstance(payload, dict) else None
    if not url:
        raise InventoryFailed(
            f"{name} returned no authorize_url. Either it does not use OAuth, "
            f"or it published no metadata — `harness mcp status {name}` says which."
        )
    return Authorization(mcp_name=name, authorize_url=str(url))


def connection_status(name: str, *, transport: Transport) -> tuple[bool, str]:
    """Whether this server is usable now, and who as."""
    status, payload = transport.get(f"/mcp/{name}/status")
    if status != 200:
        raise InventoryFailed(f"Could not read {name} ({status}): {_why(payload)}")
    body = payload if isinstance(payload, dict) else {}
    return bool(body.get("connected")), str(body.get("account") or "")


def disconnect(name: str, *, transport: Transport) -> None:
    """Forget this person's token for one server."""
    status, payload = transport.delete(f"/mcp/{name}/disconnect")
    if status not in (200, 204):
        raise InventoryFailed(
            f"Could not disconnect {name} ({status}): {_why(payload)}"
        )
