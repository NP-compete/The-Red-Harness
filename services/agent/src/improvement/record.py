"""Keeping what the improvement loop tried to do (E12-T8)."""

from __future__ import annotations

from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_KEYS = 40


def changed_keys(before: Any, after: Any, *, prefix: str = "") -> list[str]:
    """Which settings differ, by dotted name."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return [prefix] if before != after else []

    found: list[str] = []
    for key in sorted(set(before) | set(after)):
        name = f"{prefix}.{key}" if prefix else str(key)
        old, new = before.get(key), after.get(key)
        if isinstance(old, dict) or isinstance(new, dict):
            found.extend(changed_keys(old or {}, new or {}, prefix=name))
        elif old != new:
            found.append(name)
    return found


def record_proposal(
    *,
    before: Any,
    after: Any,
    permitted: bool,
    reason: str = "",
    source: str = "",
) -> None:
    """Note that a change was weighed, and how it went."""
    from agent.src.audit.events import AuditEventType

    keys = changed_keys(before, after)
    details: dict[str, Any] = {
        "keys": keys[:MAX_KEYS],
        "keys_total": len(keys),
        "permitted": permitted,
        "source": source or "unknown",
    }
    if not permitted:
        details["reason"] = reason

    try:
        from agent.src.audit import emit_audit_event

        emit_audit_event(
            AuditEventType.PROPOSAL_WEIGHED
            if permitted
            else AuditEventType.PROPOSAL_REFUSED,
            **details,
        )
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not record a proposal: %s", error)

    if permitted:
        logger.info("Proposal may go to a reviewer: %d setting(s)", len(keys))
    else:
        logger.warning(
            "Proposal refused (%d setting(s)): %s", len(keys), reason or "no reason"
        )
