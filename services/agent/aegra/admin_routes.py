"""Read-only introspection of the agent's resolved configuration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agent.aegra.eval_routes import _require_developer
from agent.src.security.credential_presence import credential_state
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/admin", tags=["admin"])


class ConfigProblemOut(BaseModel):
    """One thing wrong with the configuration, and where."""

    source: str
    detail: str


class ConfigProblemsOut(BaseModel):
    """Whether the configuration loaded cleanly, and what it found."""

    clean: bool
    problems: list[ConfigProblemOut]


class AgentIdentityOut(BaseModel):
    """What this agent is called and which model answers for it."""

    name: str | None = None
    model: str | None = None


class ToolPolicyOut(BaseModel):
    """Which tools this deployment allows."""

    decision: str
    risk: str
    reason: str


class ApprovalOut(BaseModel):
    """Which actions need a person's approval."""

    enabled: bool
    mode: str
    default_decision: str
    policy_count: int
    tools: dict[str, ToolPolicyOut]


class ExecutionOut(BaseModel):
    """Where and how this agent's work runs."""

    effects: str


class McpServerOut(BaseModel):
    """One MCP server this deployment knows about."""

    enabled: bool
    transport: str | None = None
    auth_mode: str | None = None
    credential: str


class PolicyEngineOut(BaseModel):
    """Which policy engine decides, and whether it is reachable."""

    opa_enabled: bool
    fail_open: bool


class SchemaOut(BaseModel):
    """Which layouts this build reads, and which the tree claims."""

    current: int
    oldest_supported: int
    declared: int | None = None
    deprecated: bool


class InboundOut(BaseModel):
    """Whether anything may start a run from outside, and how."""

    enabled: bool
    auth_mode: str = ""
    published_tools: int = 0
    limits: dict[str, Any] | None = None


class KnowledgeOut(BaseModel):
    """Whether the document library is on, and what it holds."""

    enabled: bool
    scopes: list[str] = []
    order: list[str] = []
    top_k: int = 0


class AdminConfigOut(BaseModel):
    """The agent's effective configuration, secrets omitted."""

    agent: AgentIdentityOut
    approval: ApprovalOut
    execution: ExecutionOut
    skills: dict[str, str]
    mcp_servers: dict[str, McpServerOut]
    policy_engine: PolicyEngineOut
    schema_: SchemaOut = Field(alias="schema")
    inbound: InboundOut
    knowledge: KnowledgeOut


_BUILTIN_TOOL_NAMES = frozenset(
    {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "write_todos",
        "task",
        "compact_conversation",
    }
)


@router.get("/config/problems", responses={200: {"model": ConfigProblemsOut}})
async def config_problems_route(
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Whether the configuration loaded cleanly, and what it found."""
    return config_problems()


def config_problems() -> dict[str, Any]:
    """What was wrong with the configuration the agent is using."""
    from agent.src.agent.config.problems import found_problems

    problems = found_problems()
    return {
        "clean": not problems,
        "problems": [{"source": p.source, "detail": p.detail} for p in problems],
    }


@router.get("/config", responses={200: {"model": AdminConfigOut}})
async def admin_config(_token: str = Depends(_require_developer)) -> dict[str, Any]:
    """Report the agent's effective configuration, secrets omitted."""
    from agent.src.agent.config import agent_config
    from agent.src.agent.config.hitl import describe_policies

    orchestrator = agent_config.get_orchestrator_config()

    approval = agent_config.resolve_agent_middleware(
        orchestrator.get("model", "")
    ).human_approval

    skills = agent_config.get_available_skills()
    servers = agent_config.get_mcp_servers()
    effects = _effects_mode()

    return {
        "agent": {
            "name": orchestrator.get("name"),
            "model": orchestrator.get("model"),
        },
        "approval": {
            "enabled": approval.enabled,
            "mode": approval.mode,
            "default_decision": approval.default_decision,
            "policy_count": len(approval.policies),
            "tools": describe_policies(
                set(skills) | set(servers) | set(_BUILTIN_TOOL_NAMES),
                approval,
                effects=effects,
            ),
        },
        "execution": {"effects": effects},
        "skills": {name: str(path) for name, path in sorted(skills.items())},
        "mcp_servers": {
            name: {
                "enabled": cfg.get("enabled", False),
                "transport": cfg.get("transport"),
                "auth_mode": cfg.get("auth_mode"),
                "credential": credential_state(cfg),
            }
            for name, cfg in sorted(servers.items())
        },
        "policy_engine": _opa_summary(),
        "schema": _schema_summary(),
        "inbound": _inbound_summary(),
        "knowledge": _knowledge_summary(),
    }


def _inbound_summary() -> dict[str, Any]:
    """Whether another system may call this agent, and on what terms."""
    from agent.src.agent.config import agent_config

    try:
        found = agent_config.get_inbound_config()
    except Exception as error:
        return {"enabled": False, "unreadable": str(error)}

    limits = found.limits
    return {
        "enabled": found.enabled,
        "auth_mode": found.auth_mode,
        "published_tools": len(found.tools),
        "limits": None
        if limits is None
        else {
            "per_second": limits.per_second,
            "burst": limits.burst,
            "daily_spend": None
            if limits.daily_spend is None
            else format(limits.daily_spend, "f"),
        },
    }


def _schema_summary() -> dict[str, Any]:
    """Which layouts this build reads, and which one the tree claims."""
    from agent.src.agent.config import agent_config
    from agent.src.agent.config.schema_version import CURRENT, OLDEST_SUPPORTED

    declared = agent_config.declared_schema_version()
    return {
        "current": CURRENT,
        "oldest_supported": OLDEST_SUPPORTED,
        "declared": declared,
        "deprecated": (declared or OLDEST_SUPPORTED) < CURRENT,
    }


def _opa_summary() -> dict[str, Any]:
    """Whether external policy evaluation is active, and how it fails."""
    try:
        from agent.src.opa.config import get_opa_fail_open, is_opa_enabled

        return {
            "opa_enabled": is_opa_enabled(),
            "fail_open": get_opa_fail_open(),
        }
    except Exception as exc:
        logger.debug("Could not read OPA config: %s", exc)
        return {"opa_enabled": None, "fail_open": None}


def _effects_mode() -> str:
    """The configured effects axis, defaulting to live."""
    from agent.src.agent.config import agent_config

    return agent_config.get_effects_mode()


def _knowledge_summary() -> dict[str, Any]:
    """Which document scopes this deployment keeps."""
    from agent.src.agent.config import agent_config

    try:
        found = agent_config.get_knowledge_config()
    except Exception as error:
        return {"enabled": False, "unreadable": str(error)}

    return {
        "enabled": found.enabled,
        "scopes": [scope.value for scope in found.scopes],
        "order": [scope.value for scope in found.order],
        "top_k": found.top_k,
    }
