"""Capability manifest resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

EXPLICIT = "explicit"
IMPLICIT_ALL_MCP = "implicit_all_mcp"
NO_MANIFEST = "no_manifest"


@dataclass(frozen=True)
class CapabilityManifest:
    """Frozen set of tool names one agent/subagent is authorized to invoke."""

    agent_name: str
    allowed_tool_names: frozenset[str]
    source: str

    def allows(self, tool_name: str) -> bool:
        """Return True if *tool_name* is authorized under this manifest."""
        return tool_name in self.allowed_tool_names

    def merged_with(self, extra_tool_names: Any) -> "CapabilityManifest":
        """Return a new manifest that additionally authorizes *extra_tool_names*."""
        return CapabilityManifest(
            agent_name=self.agent_name,
            allowed_tool_names=self.allowed_tool_names | frozenset(extra_tool_names),
            source=self.source,
        )


def resolve_capability_manifest(
    tool_names: list[str] | None,
    available_tools: list[Any],
    mcp_server_names: list[str] | None,
    agent_name: str = "agent",
) -> tuple[list[Any], CapabilityManifest]:
    """Resolve the enforced tool list and capability manifest."""
    from agent.src.agent.config import agent_config

    tools = (
        agent_config.resolve_tools(tool_names, available_tools, agent_name=agent_name)
        if tool_names
        else []
    )

    if tools:
        return list(tools), CapabilityManifest(
            agent_name=agent_name,
            allowed_tool_names=frozenset(t.name for t in tools),
            source=EXPLICIT,
        )

    if tool_names and not tools:
        logger.warning(
            "capability_explicit_empty",
            agent=agent_name,
            declared_tools=sorted(tool_names),
            message=(
                "Agent declared explicit 'tools:' but none could be resolved "
                "against available MCP server tools. The agent will have no "
                "MCP server tools. Verify tool names match MCP tool names."
            ),
        )
        return [], CapabilityManifest(
            agent_name=agent_name,
            allowed_tool_names=frozenset(),
            source=EXPLICIT,
        )

    if tool_names is None and mcp_server_names and available_tools:
        logger.info(
            "capability_implicit_grant",
            agent=agent_name,
            mcp_servers=sorted(mcp_server_names),
            tool_count=len(available_tools),
            message=(
                "Agent declared MCP server(s) without an explicit 'tools:' "
                "list -- granting every tool those servers currently expose. "
                "This tracks the server's live tool set, not a reviewed "
                "manifest; add 'tools:' to pin capabilities to what was "
                "actually reviewed."
            ),
        )
        _emit_manifest_audit_event(
            agent_name=agent_name,
            mcp_server_names=mcp_server_names,
            tool_names=[t.name for t in available_tools],
        )
        return list(available_tools), CapabilityManifest(
            agent_name=agent_name,
            allowed_tool_names=frozenset(t.name for t in available_tools),
            source=IMPLICIT_ALL_MCP,
        )

    return [], CapabilityManifest(
        agent_name=agent_name, allowed_tool_names=frozenset(), source=NO_MANIFEST
    )


def _emit_manifest_audit_event(
    *,
    agent_name: str,
    mcp_server_names: list[str],
    tool_names: list[str],
) -> None:
    """Best-effort platform audit event; never raises into the caller."""
    try:
        from agent.src.audit.emitter import emit_audit_event
        from agent.src.audit.events import AuditEventType

        emit_audit_event(
            AuditEventType.CAPABILITY_IMPLICIT_GRANT,
            agent=agent_name,
            mcp_servers=sorted(mcp_server_names),
            tools=sorted(tool_names),
        )
    except Exception:
        logger.debug("capability_audit_emit_failed", agent=agent_name, exc_info=True)
