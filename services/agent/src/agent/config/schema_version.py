"""Which configuration trees this build can load."""

from __future__ import annotations

from dataclasses import dataclass

CURRENT = 3
OLDEST_SUPPORTED = CURRENT - 1


@dataclass(frozen=True)
class Supported:
    """The config schema version is supported, perhaps deprecated."""

    version: int
    deprecated: bool


@dataclass(frozen=True)
class TooOld:
    """The config schema version is older than anything supported."""

    version: int
    message: str


@dataclass(frozen=True)
class TooNew:
    """The config schema version is newer than this build understands."""

    version: int
    message: str


Result = Supported | TooOld | TooNew


def check_schema_version(version: int | None) -> Result:
    """Check `version` against the versions this build supports."""
    if version is None:
        version = OLDEST_SUPPORTED

    if version < OLDEST_SUPPORTED:
        return TooOld(
            version=version,
            message=(
                f"This configuration is version {version}. "
                f"Migrate it to version {OLDEST_SUPPORTED} or later."
            ),
        )

    if version > CURRENT:
        return TooNew(
            version=version,
            message=(
                f"This configuration is version {version}, "
                f"but this build understands up to {CURRENT}. Upgrade the deployment."
            ),
        )

    return Supported(version=version, deprecated=version < CURRENT)
