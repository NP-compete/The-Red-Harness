"""PII middleware package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agent.src.pii.config import PIIConfig
    from agent.src.pii.scrubber import PIIScrubber

_scrubber: Optional["PIIScrubber"] = None


def init_pii_middleware(config: "PIIConfig", hash_key: bytes = b"") -> "PIIScrubber":
    """Initialise the global PII scrubber. Call once at process startup."""
    global _scrubber  # noqa: PLW0603
    from agent.src.pii.scrubber import PIIScrubber

    _scrubber = PIIScrubber(config, hash_key)
    return _scrubber


def get_scrubber() -> Optional["PIIScrubber"]:
    """Return the global PIIScrubber, or None if not yet initialised."""
    return _scrubber


__all__ = [
    "init_pii_middleware",
    "get_scrubber",
]
