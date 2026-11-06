"""Audit logging — structured events gated by PLATFORM_AUDIT_ENABLED."""

from agent.src.audit.config import is_audit_enabled
from agent.src.audit.emitter import emit_audit_event
from agent.src.audit.events import AuditEventType

__all__ = [
    "AuditEventType",
    "emit_audit_event",
    "is_audit_enabled",
]
