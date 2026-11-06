"""Filesystem permissions builder."""

from __future__ import annotations

from typing import Any, cast

from agent.src.agent.config.filesystem import (
    FilesystemFileConfig,
)
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def build_permissions(
    config: FilesystemFileConfig,
) -> list[Any] | None:
    """Build FilesystemPermission list from config."""
    if not config.permissions:
        return None

    try:
        from deepagents.middleware.filesystem import FilesystemPermission
    except ImportError:
        logger.warning(
            "FilesystemPermission not available — permissions config ignored"
        )
        return None

    permissions: list[Any] = []

    for rule in config.permissions:
        try:
            perm = FilesystemPermission(
                operations=cast("Any", rule.operations),
                paths=rule.paths,
                mode=rule.mode,
            )
            permissions.append(perm)
        except Exception as e:
            logger.warning("Skipping invalid permission rule %r: %s", rule, e)

    if permissions:
        logger.info("Built %d filesystem permission rule(s)", len(permissions))

    return permissions or None
