"""Symmetric encryption for MCP OAuth tokens and client secrets at rest."""

from __future__ import annotations

import os
from typing import cast

from cryptography.fernet import Fernet, InvalidToken

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_fernet_primary: Fernet | None = None
_fernet_previous: Fernet | None | bool = False

_primary_key: str | None = None
_superseded: Fernet | None = None


def _fernet_key_help() -> str:
    return (
        'Generate one with: python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"'
    )


class McpKeyMissingError(RuntimeError):
    """The token-encryption key is absent, or is not a Fernet key."""


def _parse_fernet_key(env_var: str) -> str:
    """The key, from the variable or from wherever it points."""
    from agent.src.security.secret_source import (
        SecretUnavailable,
        from_variable,
    )

    try:
        found = from_variable(env_var)
    except SecretUnavailable as missing:
        raise McpKeyMissingError(
            f"{env_var} points elsewhere and could not be read: {missing}. "
            f"{_fernet_key_help()}"
        ) from None

    if not found:
        raise McpKeyMissingError(
            f"{env_var} is required for MCP OAuth token storage. {_fernet_key_help()}"
        )
    return found


def _build_fernet(env_var: str) -> Fernet:
    """Construct a Fernet, reporting a bad key as configuration."""
    key = _parse_fernet_key(env_var)
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise McpKeyMissingError(
            f"{env_var} is not a valid Fernet key ({len(key)} characters; "
            f"a Fernet key is 44). {_fernet_key_help()}"
        ) from exc


def _points_elsewhere(env_var: str) -> bool:
    """Whether the variable holds a reference rather than a key."""
    return ":" in os.environ.get(env_var, "").strip()


def _get_fernet_primary() -> Fernet:
    """The key to seal with now, re-read when it can change."""
    global _fernet_primary, _primary_key, _superseded  # noqa: PLW0603

    if not _points_elsewhere("MCP_TOKEN_ENCRYPTION_KEY"):
        if _fernet_primary is None:
            _fernet_primary = _build_fernet("MCP_TOKEN_ENCRYPTION_KEY")
        return _fernet_primary

    found = _parse_fernet_key("MCP_TOKEN_ENCRYPTION_KEY")
    if _fernet_primary is None or found != _primary_key:
        replacement = _build_fernet("MCP_TOKEN_ENCRYPTION_KEY")
        _superseded = _fernet_primary
        _fernet_primary, _primary_key = replacement, found
    return _fernet_primary


def _get_fernet_previous() -> Fernet | None:
    """Return the optional previous key used during rotation."""
    global _fernet_previous  # noqa: PLW0603
    if _fernet_previous is False:
        previous_key = os.environ.get("MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS", "").strip()
        _fernet_previous = (
            _build_fernet("MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS") if previous_key else None
        )
    return cast(Fernet | None, _fernet_previous)


def reset_mcp_crypto_cache() -> None:
    """Clear cached Fernet instances (used by tests and config reload)."""
    global _fernet_primary, _fernet_previous, _primary_key, _superseded  # noqa: PLW0603
    _fernet_primary = None
    _fernet_previous = False
    _primary_key = None
    _superseded = None


def encrypt_secret(plaintext: str | None) -> str | None:
    """Encrypt a secret value for Redis/Postgres storage."""
    if plaintext is None:
        return None
    return _get_fernet_primary().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str | None) -> str | None:
    """Decrypt a value previously stored by :func:`encrypt_secret`."""
    if ciphertext is None:
        return None

    keys: list[Fernet] = [_get_fernet_primary()]
    previous = _get_fernet_previous()
    if previous is not None:
        keys.append(previous)
    if _superseded is not None:
        keys.append(_superseded)

    last_exc: InvalidToken | None = None
    for fernet in keys:
        try:
            return fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            last_exc = exc

    logger.error(
        "Failed to decrypt MCP secret — key mismatch or corrupt data",
        keys_tried=len(keys),
    )
    raise RuntimeError("MCP token decryption failed") from last_exc
