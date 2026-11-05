"""OPA authorization configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent.src.settings import settings

if TYPE_CHECKING:
    from agent.src.agent.config.opa import OpaFileConfig


def _yaml_config() -> OpaFileConfig:
    from agent.src.agent.config import agent_config

    return agent_config.get_opa_config()


def is_opa_enabled() -> bool:
    """Return whether OPA authorization is enabled."""
    if settings.OPA_ENABLED is not None:
        return settings.OPA_ENABLED
    return _yaml_config().enabled


def get_opa_url() -> str:
    """Return the OPA decision endpoint URL."""
    if settings.OPA_URL is not None:
        return settings.OPA_URL
    return _yaml_config().url


def get_opa_timeout() -> float:
    """Return the OPA request timeout in seconds."""
    if settings.OPA_TIMEOUT is not None:
        return settings.OPA_TIMEOUT
    return _yaml_config().timeout


def get_opa_max_retries() -> int:
    """Return the maximum number of OPA-blocked retries."""
    if settings.OPA_MAX_RETRIES is not None:
        return settings.OPA_MAX_RETRIES
    return _yaml_config().max_retries


def get_opa_fail_open() -> bool:
    """Return whether OPA errors should fail open (allow) or closed (deny)."""
    return _yaml_config().fail_open
