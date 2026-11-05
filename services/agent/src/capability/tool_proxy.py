"""CapabilityToolProxy — runtime enforcement point for the capability manifest."""

from __future__ import annotations

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from agent.src.capability.manifest import CapabilityManifest
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

CAPABILITY_DENIED_RESULT = (
    "[CAPABILITY_DENIED] This tool is not in the agent's authorized capability "
    "manifest and was blocked by platform policy. Do not retry this or any "
    "other unlisted tool. Tell the user this action is not available."
)


def _get_tool_call_id(input: Any) -> str:
    """Extract tool_call_id from a LangGraph ToolCall dict."""
    if isinstance(input, dict):
        return str(input.get("id", ""))
    return ""


def _make_denied_result(tool_name: str, input: Any) -> Any:
    """Return CAPABILITY_DENIED_RESULT as a ToolMessage for the graph state."""
    from langchain_core.messages import ToolMessage

    return ToolMessage(
        content=CAPABILITY_DENIED_RESULT,
        name=tool_name,
        tool_call_id=_get_tool_call_id(input),
        status="error",
    )


def _refusal(tool_name: str, reason: str, input: Any) -> Any:
    """A refusal shaped so the graph can put it on the turn."""
    from langchain_core.messages import ToolMessage

    return ToolMessage(
        content=reason,
        name=tool_name,
        tool_call_id=_get_tool_call_id(input),
        status="error",
    )


def _emit_denied_audit(tool_name: str, manifest: CapabilityManifest) -> None:
    """Best-effort platform audit event for a capability denial; never raises."""
    try:
        from agent.src.audit.emitter import emit_audit_event
        from agent.src.audit.events import AuditEventType

        emit_audit_event(
            AuditEventType.CAPABILITY_DENIED,
            agent=manifest.agent_name,
            tool=tool_name,
            manifest_source=manifest.source,
        )
    except Exception:
        logger.debug("capability_audit_emit_failed", tool=tool_name, exc_info=True)


class CapabilityToolProxy(BaseTool):
    """Transparent BaseTool wrapper that enforces manifest membership per call."""

    name: str = ""
    description: str = ""
    _inner: Any = PrivateAttr()
    _manifest: CapabilityManifest = PrivateAttr()

    def __init__(self, inner_tool: Any, manifest: CapabilityManifest) -> None:
        """Copy name/description/args_schema from inner_tool; bind the manifest."""
        schema: Optional[Type[BaseModel]] = getattr(inner_tool, "args_schema", None)
        super().__init__(
            name=getattr(inner_tool, "name", ""),
            description=getattr(inner_tool, "description", ""),
            args_schema=schema,
        )
        self._inner = inner_tool
        self._manifest = manifest

    def _denied(self) -> bool:
        """Return True and emit audit if this tool is not in the manifest."""
        if self._manifest.allows(self.name):
            return False
        logger.warning(
            "capability_denied",
            agent=self._manifest.agent_name,
            tool=self.name,
            manifest_source=self._manifest.source,
        )
        _emit_denied_audit(self.name, self._manifest)
        return True

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        """Deny immediately if the tool is outside the manifest; else delegate."""
        if self._denied():
            return _make_denied_result(self.name, input)

        from agent.src.security.tool_preflight import look_before

        looked = look_before(self._inner, input)
        if not looked.permitted:
            return _refusal(self.name, looked.reason, input)

        from agent.src.security.tool_preflight import configured_pace

        pace = configured_pace()
        run = str(id(input))
        paced = pace.may_call(self.name, run=run)
        if not paced.permitted:
            return _refusal(self.name, paced.reason, input)

        try:
            return await self._inner.ainvoke(input, config, **kwargs)
        finally:
            pace.done(self.name, run=run)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Sync fallback; same manifest check as ainvoke."""
        if self._denied():
            return CAPABILITY_DENIED_RESULT
        tool_input: Any = args[0] if args else kwargs
        return self._inner.invoke(tool_input)


def enforce_capability(tools: list[Any], manifest: CapabilityManifest) -> list[Any]:
    """Wrap every tool with a CapabilityToolProxy bound to *manifest*."""
    if not tools:
        return tools
    return [CapabilityToolProxy(t, manifest) for t in tools]
