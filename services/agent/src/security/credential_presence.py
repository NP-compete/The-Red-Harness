"""Whether a server's own credential is there, in one place."""

from __future__ import annotations

from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

NEEDS_OWN_CREDENTIAL = {"api_key", "service_token"}


def credential_state(cfg: Any) -> str:
    """One of "set", "missing", "not needed"."""
    try:
        if not isinstance(cfg, dict):
            return "not needed"
        if cfg.get("auth_mode") not in NEEDS_OWN_CREDENTIAL:
            return "not needed"

        reference = str(cfg.get("auth_env_var") or "").strip()
        if not reference:
            return "missing"

        from agent.src.security.secret_source import SecretUnavailable, resolve

        try:
            return "set" if resolve(reference) else "missing"
        except SecretUnavailable:
            return "missing"
    except Exception:
        logger.debug("Could not check a server's credential", exc_info=True)
        return "not needed"
