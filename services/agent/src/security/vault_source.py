"""A secret source backed by the vault an organisation already runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agent.src.security.secret_source import SecretUnavailable

_RENEW_AFTER = 0.8

_SCHEME = "vault://"


@dataclass(frozen=True)
class VaultReference:
    """A secret's path in Vault and the field to read from it."""

    path: str
    field: str


def parse_reference(reference: str) -> VaultReference:
    """Split `vault://team/agent/tracker#token` into path and field."""
    asked = (reference or "").strip()
    if asked.startswith(_SCHEME):
        asked = asked[len(_SCHEME) :]
    elif asked.startswith("//"):
        asked = asked[2:]

    path, separator, field = asked.partition("#")
    if not separator or not field.strip():
        raise SecretUnavailable(
            f"{reference} names no field. A vault reference reads one field of "
            "one path, written as vault://some/path#field, so that a "
            "permission to read one secret does not become a permission to "
            "read every secret beside it."
        )
    path = path.strip("/").strip()
    if not path:
        raise SecretUnavailable(f"{reference} names no path")

    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SecretUnavailable(
            f"{reference} has a path that does not read plainly. The vault "
            "enforces its own rules and a path assembled here should not be "
            "the thing testing them."
        )

    return VaultReference(path=path, field=field.strip())


def needs_renewal(*, lease_seconds: float, age_seconds: float) -> bool:
    """Whether a lease is close enough to its end to renew now."""
    if lease_seconds <= 0:
        return False
    return age_seconds >= lease_seconds * _RENEW_AFTER


def read_secret(
    reference: VaultReference,
    *,
    platform_identity: Callable[[], str | None],
    login: Callable[[str], tuple[str, int]],
    fetch: Callable[[str, str, str], str | None],
) -> str:
    """One field of one path, read with the workload's own identity."""
    identity = platform_identity()
    if not identity or not identity.strip():
        raise SecretUnavailable(
            f"vault://{reference.path}#{reference.field} cannot be read: this "
            "workload has no platform identity to present. A vault token in "
            "configuration is not an alternative — it is the copied secret "
            "this source exists to avoid."
        )

    try:
        token, _lease = login(identity)
    except Exception as error:
        raise SecretUnavailable(
            f"vault://{reference.path}#{reference.field} cannot be read: the "
            f"vault refused this workload's identity ({type(error).__name__})"
        ) from None

    try:
        value = fetch(reference.path, reference.field, token)
    except Exception as error:
        raise SecretUnavailable(
            f"vault://{reference.path}#{reference.field} cannot be read "
            f"({type(error).__name__})"
        ) from None

    if value is None or not value.strip():
        raise SecretUnavailable(
            f"vault://{reference.path}#{reference.field} is empty or absent"
        )
    return value


_ADDRESS = "VAULT_ADDR"

_ROLE = "VAULT_ROLE"

_IDENTITY_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/token"

_TIMEOUT = 10.0


def platform_identity() -> str | None:
    """The workload's own identity, as the platform projects it."""
    import os

    path = os.environ.get("VAULT_IDENTITY_FILE", _IDENTITY_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip() or None
    except OSError:
        return None


def _login(address: str, role: str) -> Callable[[str], tuple[str, int]]:
    """A login function bound to this Vault address and role."""

    def login(identity: str) -> tuple[str, int]:
        """Exchange `identity` for a Vault token and its lease."""
        import httpx

        response = httpx.post(
            f"{address.rstrip('/')}/v1/auth/kubernetes/login",
            json={"role": role, "jwt": identity},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        auth = (response.json() or {}).get("auth") or {}
        token = auth.get("client_token")
        if not token:
            raise RuntimeError("the vault returned no token")
        return token, int(auth.get("lease_duration") or 0)

    return login


def _fetch(address: str) -> Callable[[str, str, str], str | None]:
    """A fetch function bound to this Vault address."""

    def fetch(path: str, field: str, token: str) -> str | None:
        """Read one field of one secret, or `None` if it is not there."""
        import httpx

        response = httpx.get(
            f"{address.rstrip('/')}/v1/{path}",
            headers={"X-Vault-Token": token},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json() or {}
        held = (body.get("data") or {}).get("data") or body.get("data") or {}
        found = held.get(field)
        return str(found) if found is not None else None

    return fetch


def from_vault(reference: str) -> str | None:
    """Resolve a `vault://` reference, for the resolver to call."""
    import os

    parsed = parse_reference(reference)

    address = os.environ.get(_ADDRESS, "").strip()
    if not address:
        raise SecretUnavailable(
            f"vault://{parsed.path}#{parsed.field} names the vault source, "
            f"but {_ADDRESS} is not set, so there is no vault to ask."
        )
    role = os.environ.get(_ROLE, "").strip()
    if not role:
        raise SecretUnavailable(
            f"vault://{parsed.path}#{parsed.field} names the vault source, "
            f"but {_ROLE} is not set, so there is no role to log in as."
        )

    return read_secret(
        parsed,
        platform_identity=platform_identity,
        login=_login(address, role),
        fetch=_fetch(address),
    )
