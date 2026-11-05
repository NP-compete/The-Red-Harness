"""Deciding whether an address may be fetched."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class UrlCheck:
    """Whether a URL may be fetched, and why not."""

    ok: bool
    host: str = ""
    reason: str = ""


def check_url(url: str, *, allowed_hosts: list[str]) -> UrlCheck:
    """Check `url` against `allowed_hosts`, refusing anything internal."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return UrlCheck(ok=False, reason="that is not an address")

    if parsed.scheme != "https":
        return UrlCheck(ok=False, reason="only https addresses are fetched")
    if parsed.username or parsed.password:
        return UrlCheck(ok=False, reason="addresses may not carry credentials")

    host = (parsed.hostname or "").lower()
    if not host:
        return UrlCheck(ok=False, reason="that is not an address")

    if _is_internal(host):
        return UrlCheck(
            ok=False, host=host, reason="that address is on an internal network"
        )

    if host not in {h.lower() for h in allowed_hosts}:
        return UrlCheck(
            ok=False, host=host, reason="that host is not on the allowed list"
        )

    return UrlCheck(ok=True, host=host)


def _is_internal(host: str) -> bool:
    """Whether `host` is a private or otherwise internal address."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
    )
