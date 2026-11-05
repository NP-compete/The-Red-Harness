"""Platform audit configuration."""

from agent.src.settings import settings


def is_audit_enabled() -> bool:
    """Return whether platform audit is enabled."""
    return settings.PLATFORM_AUDIT_ENABLED
