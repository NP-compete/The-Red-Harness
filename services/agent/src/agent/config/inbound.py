"""Letting another system call this agent, and under whose authority."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from agent.src.security.inbound_limits import Limits

AUTH_MODES = ("oauth", "service_token")

SCOPES = ("read", "act")


class InboundMisconfigured(ValueError):
    """The inbound server is configured in a way that must not start."""


@dataclass(frozen=True)
class PublishedTool:
    """One tool this agent publishes, and the scope it needs."""

    name: str
    description: str = ""
    scope: str = "read"


@dataclass(frozen=True)
class Inbound:
    """What this agent publishes inbound, and the limits on it."""

    enabled: bool = False
    auth_mode: str = ""
    tools: tuple[PublishedTool, ...] = ()
    required_scopes: tuple[str, ...] = ()
    limits: Limits | None = None


def read_inbound(raw: Any) -> Inbound:
    """The inbound configuration, or a refusal to start."""
    section = (raw or {}).get("mcp_server") if isinstance(raw, dict) else None
    if not isinstance(section, dict):
        return Inbound()

    if not bool(section.get("enabled", False)):
        return Inbound()

    mode = str(
        (
            (section.get("auth") or {}) if isinstance(section.get("auth"), dict) else {}
        ).get("mode")
        or ""
    )
    if not mode:
        raise InboundMisconfigured(
            "The inbound server is enabled with no auth mode. Set "
            f"auth.mode to one of {', '.join(AUTH_MODES)}: it decides whose "
            "authority an inbound run carries, which is not something to "
            "inherit by omission."
        )
    if mode not in AUTH_MODES:
        raise InboundMisconfigured(
            f"Unknown auth mode {mode!r}. Only {', '.join(AUTH_MODES)} exist. "
            "An inbound run carries the caller's authority or a service "
            "identity's; it never carries the agent's own."
        )

    return Inbound(
        enabled=True,
        auth_mode=mode,
        tools=tuple(_tool(entry) for entry in (section.get("tools") or [])),
        required_scopes=tuple(
            str(s) for s in ((section.get("auth") or {}).get("required_scopes") or [])
        ),
        limits=_limits(section.get("limits")),
    )


_DEFAULT_RATE = 60.0


def _limits(section: Any) -> Limits | None:
    """Per-caller limits, or none at all."""
    if not isinstance(section, dict) or not section:
        return None

    rate = _number(section, "per_second", default=_DEFAULT_RATE)
    burst = int(_number(section, "burst", default=rate))
    cap = section.get("daily_spend")

    try:
        return Limits(
            per_second=rate,
            burst=max(burst, 1),
            daily_spend=None if cap is None else Decimal(str(cap)),
        )
    except (InvalidOperation, ValueError) as error:
        raise InboundMisconfigured(
            f"inbound limits: daily_spend {cap!r} is not an amount ({error})"
        ) from None


def _number(section: dict, field: str, *, default: float) -> float:
    """`field` as a float, or `default` if it is missing or bad."""
    raw = section.get(field)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise InboundMisconfigured(
            f"inbound limits: {field} must be a number, not {raw!r}"
        ) from None


def _tool(entry: Any) -> PublishedTool:
    """One published tool read from its declaration."""
    if not isinstance(entry, dict):
        raise InboundMisconfigured(f"A published tool is not a declaration: {entry!r}")

    name = str(entry.get("name") or "").strip()
    if not name:
        raise InboundMisconfigured("A published tool has no name")

    scope = str(entry.get("scope") or "read")
    if scope not in SCOPES:
        raise InboundMisconfigured(
            f"Tool {name!r} declares an unknown scope {scope!r}; "
            f"only {', '.join(SCOPES)} exist"
        )

    return PublishedTool(
        name=name,
        description=str(entry.get("description") or ""),
        scope=scope,
    )
