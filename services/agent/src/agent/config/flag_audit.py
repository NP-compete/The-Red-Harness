"""Every change to a capability, recorded."""

from __future__ import annotations

from agent.src.agent.config.features import Scope
from agent.src.audit.config import is_audit_enabled
from agent.src.audit.emitter import emit_audit_event
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

EVENT = "feature.flag.changed"

UNATTRIBUTED = "unknown"


def record_flag_change(
    *,
    key: str,
    scope: Scope,
    was: bool,
    now: bool,
    who: str,
) -> None:
    """Write down that a capability moved. Never raises."""
    if was == now:
        return

    who = who or UNATTRIBUTED
    details = {
        "key": key,
        "scope": scope.value,
        "was": was,
        "now": now,
        "who": who,
    }

    try:
        emit_audit_event(EVENT, **details)

        if scope is Scope.DEPLOYMENT and not is_audit_enabled():
            logger.warning(
                "feature_flag_changed_with_audit_disabled",
                key=key,
                scope=scope.value,
                was=was,
                now=now,
                who=who,
            )
    except Exception:
        logger.debug("Could not record a flag change", exc_info=True)
