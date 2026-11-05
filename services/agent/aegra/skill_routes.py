"""What this agent is made of — skills, subagents, and its prompt."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent.src.agent.config.parser import parse_frontmatter
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["skills"])


def _describe(path: Any) -> tuple[str, str]:
    """The skill's description, and what stopped it being read."""
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        return "", "This skill has no SKILL.md"
    try:
        meta = parse_frontmatter(skill_md)
    except Exception:
        logger.debug("Could not parse frontmatter for %s", skill_md, exc_info=True)
        return "", "Its SKILL.md could not be read"
    description = meta.get("description") or ""
    return " ".join(str(description).split()), ""


class SkillOut(BaseModel):
    """One skill: what it is called and what it is for."""

    model_config = {"extra": "allow"}

    name: str
    description: str = ""
    problem: str = ""
    agents: list[str] = []
    attached: bool = False


class SkillsOut(BaseModel):
    """Every skill available to this agent."""

    skills: list[SkillOut]


class SkillFileOut(BaseModel):
    """One readable file from a skill or subagent directory."""

    model_config = {"extra": "allow"}

    path: str
    content: str = ""
    truncated: bool = False
    frontmatter: dict[str, Any] | None = None
    body: str | None = None


class SkillFilesOut(BaseModel):
    """A skill's files, with their text."""

    name: str
    files: list[SkillFileOut]


class SubagentOut(BaseModel):
    """One subagent: its name, model and purpose."""

    model_config = {"extra": "allow", "protected_namespaces": ()}

    name: str
    description: str = ""
    model: str = ""
    provider: str = ""
    fallback: str = ""
    mcps: list[str] = []


class SubagentsOut(BaseModel):
    """Every subagent this agent delegates to."""

    subagents: list[SubagentOut]


@router.get("/skills", responses={200: {"model": SkillsOut}})
async def list_skills() -> dict[str, Any]:
    """Skills this agent has, and which of its agents use each one."""
    from agent.src.agent.config import agent_config

    available = agent_config.get_available_skills()

    users: dict[str, list[str]] = {}
    orchestrator = agent_config.get_orchestrator_config()
    for name in orchestrator.get("skills") or []:
        users.setdefault(str(name), []).append(
            str(orchestrator.get("name") or "orchestrator")
        )
    for agent_name, cfg in (agent_config.get_all_subagent_configs() or {}).items():
        for name in cfg.get("skills") or []:
            users.setdefault(str(name), []).append(str(agent_name))

    described = {name: _describe(path) for name, path in available.items()}
    skills = [
        {
            "name": name,
            "description": description,
            "problem": problem,
            "agents": sorted(users.get(name, [])),
            "attached": bool(users.get(name)),
        }
        for name, (description, problem) in described.items()
    ]

    skills.sort(key=lambda s: (not s["attached"], s["name"]))
    return {"skills": skills}


_READABLE_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt", ".py", ".sh"}

_MAX_FILE_BYTES = settings.SKILL_MAX_FILE_BYTES


@router.get("/skills/{name}", responses={200: {"model": SkillFilesOut}})
async def read_skill(name: str) -> dict[str, Any]:
    """The full source of one skill, for read-only display."""
    from fastapi import HTTPException

    from agent.src.agent.config import agent_config

    available = agent_config.get_available_skills()
    root = available.get(name)
    if root is None:
        raise HTTPException(status_code=404, detail=f"No such skill: {name}")

    root = root.resolve()
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _READABLE_SUFFIXES:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            logger.warning("Skipping %s: escapes its skill directory", path)
            continue
        try:
            raw = await asyncio.to_thread(resolved.read_bytes)
        except OSError:
            logger.debug("Could not read %s", resolved, exc_info=True)
            continue
        truncated = len(raw) > _MAX_FILE_BYTES
        text = raw[:_MAX_FILE_BYTES].decode("utf-8", errors="replace")
        entry: dict[str, Any] = {
            "path": str(resolved.relative_to(root)),
            "content": text,
            "truncated": truncated,
        }

        if resolved.suffix.lower() == ".md" and not truncated:
            try:
                meta = parse_frontmatter(resolved)
            except Exception:
                logger.debug("No usable frontmatter in %s", resolved, exc_info=True)
            else:
                body = meta.pop("body", None)
                if meta:
                    entry["frontmatter"] = {k: meta[k] for k in sorted(meta)}
                if isinstance(body, str):
                    entry["body"] = body

        files.append(entry)

    files.sort(key=lambda f: (f["path"] != "SKILL.md", f["path"]))
    return {"name": name, "files": files}


def _split_markdown(path: Path) -> dict[str, Any]:
    """A markdown file as frontmatter plus body."""
    raw = path.read_bytes()
    truncated = len(raw) > _MAX_FILE_BYTES
    text = raw[:_MAX_FILE_BYTES].decode("utf-8", errors="replace")
    entry: dict[str, Any] = {
        "path": path.name,
        "content": text,
        "truncated": truncated,
    }
    if not truncated:
        try:
            meta = parse_frontmatter(path)
        except Exception:
            logger.debug("No usable frontmatter in %s", path, exc_info=True)
        else:
            body = meta.pop("body", None)
            if meta:
                entry["frontmatter"] = {k: meta[k] for k in sorted(meta)}
            if isinstance(body, str):
                entry["body"] = body
    return entry


def _model_name(model: Any) -> str:
    """The model's name, however it was declared."""
    if isinstance(model, dict):
        return str(model.get("name") or "")
    return str(model or "")


def _model_provider(model: Any) -> str:
    """Who serves it, when the configuration says."""
    return str(model.get("provider") or "") if isinstance(model, dict) else ""


@router.get("/subagents", responses={200: {"model": SubagentsOut}})
async def list_subagents() -> dict[str, Any]:
    """The specialists this agent delegates to."""
    from agent.src.agent.config import agent_config

    out = []
    for name, cfg in sorted((agent_config.get_all_subagent_configs() or {}).items()):
        out.append(
            {
                "name": name,
                "description": " ".join(str(cfg.get("description") or "").split()),
                "model": _model_name(cfg.get("model")),
                "provider": _model_provider(cfg.get("model")),
                "fallback": _model_name(
                    cfg.get("model", {}).get("fallback")
                    if isinstance(cfg.get("model"), dict)
                    else None
                ),
                "mcps": sorted(str(m) for m in (cfg.get("mcps") or [])),
                "skills": sorted(str(s) for s in (cfg.get("skills") or [])),
                "tools": sorted(str(t) for t in (cfg.get("tools") or [])),
                "tool_scope": (
                    "explicit"
                    if cfg.get("tools")
                    else ("inherited" if cfg.get("mcps") else "none")
                ),
            }
        )
    return {"subagents": out}


def _subagent_file(name: str) -> Path:
    """Resolve a subagent's markdown, refusing anything outside the dir."""
    from fastapi import HTTPException

    from agent.src.agent.config import agent_config

    if name not in (agent_config.get_all_subagent_configs() or {}):
        raise HTTPException(status_code=404, detail=f"No such subagent: {name}")
    path = (agent_config.base_dir / "subagents" / f"{name}.md").resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No such subagent: {name}")
    return path


@router.get("/subagents/{name}", responses={200: {"model": SkillFilesOut}})
async def read_subagent(name: str) -> dict[str, Any]:
    """One subagent's definition, for read-only display."""
    return {"name": name, "files": [_split_markdown(_subagent_file(name))]}


class WhoamiOut(BaseModel):
    """Who the caller is, as the agent resolved them."""

    user_id: str
    role: str = ""
    is_developer: bool = False


class ConfiguredModelOut(BaseModel):
    """One model this deployment is configured to use."""

    model_config = {"extra": "allow", "protected_namespaces": ()}

    role: str
    name: str = ""
    provider: str = ""
    used_by: str = ""
    inherited: bool | None = None


class RoutingTierOut(BaseModel):
    """One routing tier: which model answers which kind of turn."""

    model_config = {"extra": "allow", "protected_namespaces": ()}

    tier: str
    name: str = ""
    provider: str = ""
    criteria: str = ""


class RoutingOut(BaseModel):
    """How a turn is routed between models."""

    model_config = {"extra": "allow"}

    enabled: bool = False
    strategy: str = ""
    tiers: list[RoutingTierOut] = []


class ConfiguredModelsOut(BaseModel):
    """Every model configured, and how routing chooses between them."""

    models: list[ConfiguredModelOut]
    routing: RoutingOut | None = None


class ToolPolicyOut(BaseModel):
    """Which tools are allowed, and which are denied outright."""

    model_config = {"extra": "allow"}

    tools: list[str] = []
    decision: str = ""
    risk: str = ""
    reason: str = ""


class ApprovalPolicyOut(BaseModel):
    """Which tool calls a person has to approve first."""

    model_config = {"extra": "allow"}

    enabled: bool = False
    default_decision: str = ""
    policies: list[ToolPolicyOut] = []


class PermissionsOut(BaseModel):
    """What this caller may do, as policy decided."""

    model_config = {"extra": "allow"}

    approval: ApprovalPolicyOut


class SafeguardOut(BaseModel):
    """One safeguard: what it guards and whether it is on."""

    model_config = {"extra": "allow"}

    enabled: bool = False


class PiiSafeguardOut(SafeguardOut):
    """PII scrubbing: whether it runs, and over which rules."""

    entities: list[str] = []
    trace_strategy: str = ""


class SafeguardsOut(BaseModel):
    """Which protections are on, for a page that claims they are."""

    model_config = {"extra": "allow"}

    pii: PiiSafeguardOut
    guardrail: SafeguardOut
    token_budget: SafeguardOut
    audit: SafeguardOut


@router.get("/prompt", responses={200: {"model": SkillFilesOut}})
async def read_prompt() -> dict[str, Any]:
    """The orchestrator's prompt — its identity, routing and rules."""
    from fastapi import HTTPException

    from agent.src.agent.config.paths import config_file

    path = config_file("prompt")
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="No prompt configured")
    return {"name": path.name, "files": [_split_markdown(path)]}


def _provider_of(model: str) -> str:
    """Which provider serves this name."""
    from agent.src.agent.llm import (
        is_claude_model,
        is_openai_model,
        is_vertex_model,
    )

    name = (model or "").strip()
    if not name:
        return "unknown"
    if is_claude_model(name):
        return "anthropic-vertex"
    if is_vertex_model(name):
        return "google-vertex"
    if is_openai_model(name):
        return "openai"
    return "openai-compatible"


@router.get("/models", responses={200: {"model": ConfiguredModelsOut}})
async def list_models() -> dict[str, Any]:
    """Which model answers, and which model each subagent uses."""
    from agent.src.agent.config import agent_config

    def _name_of(raw: Any) -> str:
        if isinstance(raw, dict):
            return str(raw.get("name") or "").strip()
        return str(raw or "").strip()

    entries: list[dict[str, Any]] = []

    orchestrator = ""
    try:
        orchestrator = _name_of(
            (agent_config.get_orchestrator_config() or {}).get("model")
        )
    except Exception:
        logger.debug("Could not read the orchestrator model", exc_info=True)
    if orchestrator:
        entries.append(
            {
                "role": "orchestrator",
                "name": orchestrator,
                "provider": _provider_of(orchestrator),
                "used_by": "The agent itself — every turn that is not delegated.",
            }
        )

    try:
        subagents = agent_config.get_all_subagent_configs() or {}
    except Exception:
        logger.debug("Could not read subagent configs", exc_info=True)
        subagents = {}

    for name in sorted(subagents):
        cfg = subagents.get(name) or {}
        model = _name_of(cfg.get("model")) or orchestrator
        entries.append(
            {
                "role": "subagent",
                "name": model,
                "provider": _provider_of(model),
                "used_by": name,
                "inherited": not _name_of(cfg.get("model")),
            }
        )

    profiles: dict[str, Any] = {}
    try:
        raw = agent_config.get_providers_config().harness_profiles
        if isinstance(raw, dict):
            profiles = raw
    except Exception:
        logger.debug("Could not read harness profiles", exc_info=True)

    for entry in entries:
        profile = profiles.get(entry["name"])
        if profile is None:
            continue
        excluded_tools = [
            str(t) for t in (getattr(profile, "excluded_tools", None) or [])
        ]
        excluded_middleware = [
            str(m) for m in (getattr(profile, "excluded_middleware", None) or [])
        ]
        if excluded_tools:
            entry["excluded_tools"] = sorted(excluded_tools)
        if excluded_middleware:
            entry["excluded_middleware"] = sorted(excluded_middleware)

    routing: dict[str, Any] = {"enabled": False, "tiers": []}
    try:
        from agent.src.routing.config import load_router_config

        router_cfg = load_router_config()
        routing = {
            "enabled": bool(router_cfg.enabled),
            "strategy": router_cfg.strategy,
            "tiers": [
                {
                    "tier": tier.name,
                    "name": tier.model,
                    "provider": _provider_of(tier.model),
                    "criteria": tier.criteria,
                }
                for tier in router_cfg.tiers
            ],
        }
    except Exception:
        logger.debug("Could not read the router config", exc_info=True)

    return {"models": entries, "routing": routing}


@router.get("/safeguards", responses={200: {"model": SafeguardsOut}})
async def list_safeguards() -> dict[str, Any]:
    """What is applied to a message besides the model."""
    from agent.src.agent.config import agent_config

    def _read(fn: str, default: Any) -> Any:
        try:
            return getattr(agent_config, fn)()
        except Exception:
            logger.debug("Could not read config via %s", fn, exc_info=True)
            return default

    pii = _read("get_custom_pii_config", None)
    guardrail = _read("get_guardrails_config", None)
    budget = _read("get_token_budget_config", None)

    return {
        "pii": {
            "enabled": bool(getattr(pii, "enabled", False)),
            "entities": sorted(
                str(rule.name)
                for rule in (getattr(pii, "rules", None) or [])
                if rule.name
            ),
            "trace_strategy": str(getattr(pii, "trace_strategy", "") or ""),
        },
        "guardrail": {"enabled": bool(getattr(guardrail, "enabled", False))},
        "token_budget": {"enabled": bool(getattr(budget, "enabled", False))},
        "audit": {"enabled": _audit_enabled()},
    }


def _audit_enabled() -> bool:
    """Whether platform audit is switched on for this deployment."""
    from agent.src.audit.config import is_audit_enabled

    try:
        return bool(is_audit_enabled())
    except Exception:
        logger.debug("Could not read the audit setting", exc_info=True)
        return False


@router.get("/permissions", responses={200: {"model": PermissionsOut}})
async def list_permissions() -> dict[str, Any]:
    """What this agent is allowed to do."""
    from agent.src.agent.config import agent_config

    def _read(fn: str) -> Any:
        try:
            return getattr(agent_config, fn)()
        except Exception:
            logger.debug("Could not read config via %s", fn, exc_info=True)
            return None

    middleware = _read("get_middleware_config")
    approval = getattr(getattr(middleware, "defaults", None), "human_approval", None)
    filesystem = _read("get_filesystem_config")

    from agent.aegra.admin_routes import _effects_mode

    try:
        effects = _effects_mode()
    except Exception:
        logger.debug("Could not read the effects mode", exc_info=True)
        effects = "live"

    policies = [
        {
            "tools": sorted(str(t) for t in (getattr(policy, "tools", None) or [])),
            "decision": str(getattr(policy, "decision", "ask")),
            "risk": str(getattr(policy, "risk", "medium")),
            "reason": str(getattr(policy, "reason", "") or ""),
        }
        for policy in (getattr(approval, "policies", None) or [])
    ]

    never_asks = sorted(str(p) for p in (getattr(approval, "exclude", None) or []))

    rules = []
    for rule in getattr(filesystem, "permissions", None) or []:
        rules.append(
            {
                "operations": sorted(
                    str(o) for o in (getattr(rule, "operations", None) or [])
                ),
                "paths": sorted(str(p) for p in (getattr(rule, "paths", None) or [])),
                "mode": str(getattr(rule, "mode", "") or ""),
            }
        )

    return {
        "approval": {
            "enabled": bool(getattr(approval, "enabled", True)),
            "default_decision": str(getattr(approval, "default_decision", "ask")),
            "policies": policies,
            "never_asks": never_asks,
        },
        "effects": effects,
        "dry_run": effects == "dry_run",
        "filesystem": {"rules": rules},
    }


@router.get("/auth/whoami", responses={200: {"model": WhoamiOut}})
async def whoami(request: Request) -> dict[str, Any]:
    """Who this credential belongs to, and whether it is privileged."""
    from agent.aegra.auth import ENABLE_AUTH
    from agent.aegra.auth_helpers import authenticated_user_id
    from agent.src.ldap import PRIVILEGED_ROLES, resolve_user_role

    user_id = await authenticated_user_id(request, reject_anonymous=ENABLE_AUTH)

    if not ENABLE_AUTH:
        return {"user_id": user_id, "role": "owners", "is_developer": True}

    from agent.aegra.auth_helpers import role_identity

    try:
        role = await resolve_user_role(await role_identity(request) or user_id)
    except Exception:
        logger.debug("Could not resolve role for %s", user_id, exc_info=True)
        role = None

    return {
        "user_id": user_id,
        "role": role,
        "is_developer": role in PRIVILEGED_ROLES if role is not None else None,
    }
