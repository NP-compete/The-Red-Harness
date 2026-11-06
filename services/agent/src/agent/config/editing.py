"""Applying a set of edits, together or not at all."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from agent.src.agent.config.overlay import Version
from agent.src.audit.emitter import emit_audit_event
from agent.src.audit.events import AuditEventType
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _fingerprint(content: str) -> str:
    """Enough to tell two versions apart, and no use to a reader."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def _record(event_type: str, **details: Any) -> None:
    """Note something for the trail, never at the cost of the edit."""
    try:
        emit_audit_event(event_type, **details)
    except Exception:
        logger.debug("Could not record a configuration change", exc_info=True)


class EditRefused(ValueError):
    """The proposed configuration would not be valid."""

    def __init__(self, findings: list[Any]) -> None:
        """Record the findings that stopped the edit."""
        self.findings = findings
        super().__init__(
            "; ".join(
                f"{one.file}:{one.location}: {one.message}"
                if getattr(one, "location", "")
                else f"{one.file}: {one.message}"
                for one in findings
            )
            or "the proposed configuration is not valid"
        )


class _Candidate:
    """What the configuration would say if these edits were kept."""

    def __init__(self, beneath: Any, proposed: Mapping[str, str]) -> None:
        """Lay `proposed` over `beneath` without writing anything."""
        self._beneath = beneath
        self._proposed = dict(proposed)

    @property
    def generation(self) -> int:
        """The real overlay's, not zero."""
        return int(getattr(self._beneath, "generation", 0))

    def current(self, path: str) -> str | None:
        """The proposed content of `path`, or what lies beneath."""
        if path in self._proposed:
            return self._proposed[path]
        found: str | None = self._beneath.current(path)
        return found


def apply_all(overlay: Any, edits: Mapping[str, str], *, author: str) -> list[Version]:
    """Validate these edits together and keep them, or keep none."""
    if not edits:
        return []

    from agent.src.agent.config import resolution
    from agent.src.agent.config.paths import config_root
    from agent.src.agent.config.validate import validate_config

    was = resolution._overlay
    resolution.use_overlay(_Candidate(overlay, edits))
    try:
        report = validate_config(config_root())
    finally:
        resolution.use_overlay(was)

    if report.errors:
        _record(
            AuditEventType.CONFIG_EDIT_REFUSED,
            author=author,
            paths=sorted(edits),
            reason="; ".join(f"{one.file}:{one.location}" for one in report.errors),
        )
        raise EditRefused(report.errors)

    written: list[Version] = []
    for path, content in sorted(edits.items()):
        version = overlay.apply(path, content, author=author)
        written.append(version)
        _record(
            AuditEventType.CONFIG_EDITED,
            path=version.path,
            version=version.version,
            author=version.author,
            at=version.at,
            fingerprint=_fingerprint(content),
        )
    return written
