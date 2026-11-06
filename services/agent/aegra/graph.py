"""Graph factory for Aegra deployment."""

import hashlib
import json
import os
import sys
import time
from typing import Any

from langgraph_sdk.runtime import ServerRuntime

from agent._root import PACKAGE_ROOT
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_REPO_ROOT = PACKAGE_ROOT

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.environ.setdefault("PYTHONPATH", str(_REPO_ROOT))

_startup_done = False  # noqa: E402

_graph_cache: dict[str, Any] = {}
_graph_cache_ts: dict[str, float] = {}
_MAX_GRAPH_CACHE_SIZE = settings.GRAPH_CACHE_MAX_SIZE

_SAFETY_STOP_INSTRUCTION = """
## Content Safety (Enforced by Framework)

If any tool, subagent, or skill response contains the phrase "blocked due to content safety policy issue":
- **STOP ALL WORK IMMEDIATELY.**
- Do NOT retry the tool or subagent.
- Do NOT rephrase the request and try again.
"""

_CAPABILITY_RESTRICTION_INSTRUCTION = """
## Capability Restrictions (Enforced by Platform)

Your available tools are restricted by a platform-enforced capability manifest.
You ONLY have access to the tools explicitly listed in your tool list.
If a user asks for something that requires a tool you do not have:
- Tell the user clearly: "I don't have access to that capability."
- Do NOT attempt to work around it using MCP resource reads or other tools.
- Do NOT retry or loop trying alternative approaches.
- Suggest the user contact the agent builder to update the tool permissions.
"""


def _append_safety_stop_instruction(system_prompt: str) -> str:
    """Append the framework-level content safety stop instruction to any system prompt."""
    return system_prompt.rstrip() + "\n" + _SAFETY_STOP_INSTRUCTION


def _append_capability_restriction(system_prompt: str) -> str:
    """Append capability restriction instructions when manifest is explicit."""
    return system_prompt.rstrip() + "\n" + _CAPABILITY_RESTRICTION_INSTRUCTION


def _append_memory_instructions(system_prompt: str) -> str:
    """Append platform memory instructions (not from the config volume)."""
    from agent.src.memory.instructions import (
        append_memory_instructions,
        use_compact_memory_prompt,
    )

    use_compact_memory_prompt()
    return append_memory_instructions(system_prompt)


def _record_build(start_mono: float, *, cache_hit: bool, tools: int) -> None:
    """How long the graph took, and whether it was built at all."""
    took = time.monotonic() - start_mono
    try:
        from agent.aegra.otel import record_graph_built

        record_graph_built(start_mono, cache_hit=cache_hit, mcp_tool_count=tools)
    except Exception:  # pragma: no cover - telemetry is never fatal
        logger.debug("Could not record the graph build", exc_info=True)
    logger.info(
        "Graph %s in %.0fms (%d tool(s))",
        "served from cache" if cache_hit else "built",
        took * 1000,
        tools,
    )


def invalidate_graph_cache() -> None:
    """Clear the compiled graph cache (e.g. after MCP OAuth connect)."""
    global _graph_cache, _graph_cache_ts  # noqa: PLW0603
    _graph_cache.clear()
    _graph_cache_ts.clear()


def _document_search_tool() -> Any:
    """Searching the agent's documents, when it keeps any."""
    from agent.src.agent.config import agent_config

    try:
        config = agent_config.get_knowledge_config()
        if not config.enabled:
            return None

        from agent.src.knowledge.store import session_store
        from agent.src.knowledge.tools import build_retrieval_tool

        return build_retrieval_tool(config=config, store=session_store())
    except Exception as error:
        logger.warning("Document search unavailable: %s", error)
        return None


def _artifact_tools() -> list[Any]:
    """Keeping a small structured value, when the library is on."""
    from agent.src.agent.config import agent_config

    try:
        config = agent_config.get_knowledge_config()
        if not config.enabled:
            return []

        from agent.src.knowledge.artifact_tools import build_artifact_tools
        from agent.src.knowledge.artifacts import session_artifacts

        built = build_artifact_tools(store=session_artifacts(), enabled=True)
        logger.info("Artifact tools offered: %d", len(built))
        return built
    except Exception as error:
        logger.warning("Artifact store unavailable: %s", error)
        return []


def _graph_fingerprint(
    model_name: str,
    system_prompt: str,
    tool_names: list[str],
    hitl_enabled: bool = False,
    hitl_mode: str = "all",
    hitl_exclude: list[str] | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    mcp_names: list[str] | None = None,
    resource_uris: list[str] | None = None,
    user_identity: str = "",
) -> str:
    """Stable fingerprint for graph cache keying."""
    hitl_flag = (
        f"hitl={int(hitl_enabled)}"
        f",mode={hitl_mode}"
        f",exclude={','.join(sorted(hitl_exclude or []))}"
    )
    model_flag = f"temp={temperature},max_tokens={max_tokens}"
    mcp_flag = ",".join(sorted(mcp_names or []))
    resources_flag = ",".join(sorted(resource_uris or []))
    from agent.src.agent.config import agent_config
    from agent.src.agent.config.resolution import overlay_generation

    raw = (
        f"{model_name}\0{system_prompt}\0{','.join(sorted(tool_names))}"
        f"\0{hitl_flag}\0{model_flag}\0{mcp_flag}\0{resources_flag}"
        f"\0user={user_identity}\0config={overlay_generation()}"
        f"\0tree={agent_config.generation()}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def _ensure_startup() -> None:  # noqa: E402
    """Run startup orchestrator once (lazy, on first request)."""
    global _startup_done  # noqa: PLW0603
    if _startup_done:
        return
    from agent.aegra.startup import run_startup

    await run_startup()
    _startup_done = True


def _resolve_personalization_uid(user: Any, token: str | None) -> str | None:
    """Extract the user ID the BFF uses for memory preferences."""
    if not token:
        return None
    try:
        import base64

        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        return (
            claims.get("preferred_username")
            or claims.get("sub")
            or getattr(user, "identity", None)
        )
    except Exception:
        return None


def _personalization_uid(runtime: Any, user: Any, token: str | None) -> str | None:
    """Resolve memory-prefs user id: JWT (prod), then run metadata, then identity."""
    from agent.src.infrastructure.backend import _get_user_id_from_runtime
    from agent.utils.pylogger import _user_id_var

    return (
        _resolve_personalization_uid(user, token)
        or _get_user_id_from_runtime(runtime)
        or _user_id_var.get()
        or (getattr(user, "identity", None) if user else None)
    )


def _rule_lookup_ids(
    user_identity: str | None, personalization_uid: str | None
) -> list[str]:
    """Same owner key Settings uses: BFF username / X-User-ID, not JWT sub."""
    uid = personalization_uid or user_identity
    return [uid] if uid else []


async def _active_rule_contents(user_ids: list[str]) -> list[str]:
    """Active rule texts for any of *user_ids*, de-duplicated by content."""
    if not user_ids:
        return []
    from agent.src.cache.personalization_cache import get_rules, set_rules
    from agent.src.personalization.repository import PersonalizationRepository
    from agent.src.settings import settings as app_settings

    contents: list[str] = []
    seen: set[str] = set()
    repo: PersonalizationRepository | None = None
    for uid in user_ids:
        cached = await get_rules(uid)
        if cached is not None:
            batch = [r["content"] for r in cached if r.get("content")]
        else:
            if repo is None:
                repo = PersonalizationRepository(app_settings.database_uri)
            rules = await repo.list_rules(uid, active_only=True)
            batch = [r.content for r in rules]
            await set_rules(uid, [{"content": r.content} for r in rules])
        for text in batch:
            if text not in seen:
                seen.add(text)
                contents.append(text)
    return contents


def _exclude_resource_read_from_eviction() -> None:
    """Ensure ``mcp_read_resource`` is on the FilesystemMiddleware eviction skip list."""
    from deepagents.middleware import filesystem as _fs

    from agent.aegra.mcp_resource_tools import READ_TOOL

    if READ_TOOL not in _fs.TOOLS_EXCLUDED_FROM_EVICTION:
        _fs.TOOLS_EXCLUDED_FROM_EVICTION = (  # type: ignore[assignment]
            *_fs.TOOLS_EXCLUDED_FROM_EVICTION,
            READ_TOOL,
        )


def _mcp_pool(orchestrator_cfg: dict[str, Any]) -> list[str]:
    """Every MCP server this agent configuration can reach."""
    from agent.src.agent.config import agent_config

    names: set[str] = set(orchestrator_cfg.get("mcps") or [])
    try:
        for sub_cfg in (agent_config.get_all_subagent_configs() or {}).values():
            names.update(sub_cfg.get("mcps") or [])
    except Exception:
        logger.warning("Could not read subagent MCP lists", exc_info=True)
    return sorted(names)


async def agent(runtime: ServerRuntime) -> Any:
    """Async graph factory — invoked per-request by Aegra."""
    await _ensure_startup()
    _exclude_resource_read_from_eviction()

    from deepagents import create_deep_agent

    from agent.aegra.mcp import (
        get_mcp_tools,
        refresh_access_token,
        set_mcp_auth_context,
    )
    from agent.aegra.mcp_host import enter_mcp_session_scope
    from agent.aegra.mcp_resource_tools import get_mcp_resource_tools
    from agent.aegra.mcp_tool_auth import (
        clear_auth_requests,
        wrap_mcp_tools_for_auth,
    )
    from agent.src.agent.config import agent_config
    from agent.src.infrastructure.async_tasks import build_async_middleware
    from agent.src.infrastructure.backend import get_configured_backend
    from agent.src.infrastructure.providers import (
        register_profiles_from_config,
    )
    from agent.src.infrastructure.subagents import load_subagents

    user = getattr(runtime, "user", None)
    sso_token = getattr(user, "access_token", None) if user else None
    refresh_token = getattr(user, "refresh_token", None) if user else None
    user_identity = getattr(user, "identity", None) if user else None

    if sso_token:
        sso_token = await refresh_access_token(
            sso_token, refresh_token, user_id=user_identity
        )
        from agent.aegra.mcp import _user_token_cache

        cached = _user_token_cache.get(user_identity) if user_identity else None
        if cached:
            refresh_token = cached[1]

    set_mcp_auth_context(sso_token, refresh_token, user_identity)
    clear_auth_requests()
    await enter_mcp_session_scope()
    orchestrator_cfg = agent_config.get_orchestrator_config()
    agent_name = orchestrator_cfg.get("name", "orchestrator")
    orch_model_raw = orchestrator_cfg.get("model", settings.DEFAULT_MODEL)
    system_prompt = orchestrator_cfg.get("body", "")
    skill_paths = orchestrator_cfg.get("skill_paths", [])
    tool_names = orchestrator_cfg.get("tools")
    mcp_server_names = orchestrator_cfg.get("mcps", [])
    mcp_pool_names = _mcp_pool(orchestrator_cfg)

    personalization_uid = _personalization_uid(runtime, user, sso_token)

    from agent.src.infrastructure.middleware import set_user_info

    _user_display_name = getattr(user, "display_name", None) if user else None
    _user_email = getattr(user, "email", None) if user else None
    set_user_info(
        user_id=personalization_uid or user_identity,
        display_name=_user_display_name,
        email=_user_email,
    )

    if not user_identity and not personalization_uid:
        logger.info("No user identity — skipping personalization rules")
    else:
        try:
            from agent.src.personalization.injector import inject_rules

            rule_contents = await _active_rule_contents(
                _rule_lookup_ids(user_identity, personalization_uid)
            )
            system_prompt = inject_rules(system_prompt, rule_contents)
            if rule_contents:
                logger.debug(
                    "Personalization: injected %d rule(s) for user",
                    len(rule_contents),
                )
            else:
                logger.debug("Personalization: no active rules found")
        except Exception:
            logger.warning(
                "Personalization unavailable, continuing without rules",
                exc_info=True,
            )

    from agent.src.agent.config.model import parse_model_config
    from agent.src.cache.model_cache import get_or_create_model_from_spec

    orch_spec = parse_model_config(orch_model_raw)
    model_name = orch_spec.name

    model_params = agent_config.get_model_params(orch_spec.name)
    orch_temperature = model_params.get("temperature", 0.0)
    orch_max_tokens = model_params.get("max_tokens") or None

    logger.info(
        "Building agent '%s' (model=%s, provider=%s, temp=%s, max_tokens=%s, mcp_auth=%s)",
        agent_name,
        orch_spec.name,
        orch_spec.provider.value,
        orch_temperature,
        orch_max_tokens or "default",
        bool(sso_token),
    )

    model = get_or_create_model_from_spec(
        orch_spec,
        temperature=float(orch_temperature),
        max_output_tokens=int(orch_max_tokens) if orch_max_tokens else None,
    )

    providers_config = agent_config.get_providers_config()
    register_profiles_from_config(providers_config)

    mcp_tools = await get_mcp_tools(
        sso_token=sso_token,
        server_names=mcp_pool_names or None,
        user_id=user_identity,
    )
    mcp_tools = wrap_mcp_tools_for_auth(mcp_tools)

    from agent.src.infrastructure.subagents import (
        _filter_tools_by_mcp_names,
    )

    all_available_tools = _filter_tools_by_mcp_names(list(mcp_tools), mcp_server_names)

    _library = _document_search_tool()
    if _library is not None:
        all_available_tools.append(_library)
    logger.info(
        "Local tools offered to the manifest: search=%s, mcp=%d",
        _library is not None,
        len(all_available_tools) - (1 if _library is not None else 0),
    )

    all_available_tools.extend(_artifact_tools())

    from agent.src.scheduling.tools import build_schedule_tools

    all_available_tools.extend(build_schedule_tools())

    from agent.src.background.tools import build_background_tools

    all_available_tools.extend(build_background_tools())

    from agent.src.capability import (
        enforce_capability,
        resolve_capability_manifest,
    )

    tools, capability_manifest = resolve_capability_manifest(
        tool_names, all_available_tools, mcp_server_names, agent_name=agent_name
    )

    resource_tools = wrap_mcp_tools_for_auth(
        get_mcp_resource_tools(
            server_names=mcp_pool_names or None,
            allowed_uris=orchestrator_cfg.get("resources") or None,
        )
    )

    from agent.src.capability.manifest import EXPLICIT as _EXPLICIT

    if resource_tools and capability_manifest.source != _EXPLICIT:
        capability_manifest = capability_manifest.merged_with(
            t.name for t in resource_tools
        )
        tools.extend(resource_tools)

    tools = enforce_capability(tools, capability_manifest)

    if capability_manifest.source == _EXPLICIT:
        system_prompt = _append_capability_restriction(system_prompt)

    from agent.src.infrastructure.middleware import (
        build_middleware_list,
        resolve_memory_param,
    )

    middleware_overrides = orchestrator_cfg.get("middleware")
    resolved_mw = agent_config.resolve_agent_middleware(
        model_name, middleware_overrides
    )

    user_memory_enabled = settings.MEMORY_ENABLED
    if settings.MEMORY_ENABLED and personalization_uid:
        try:
            from agent.src.personalization.repository import (
                PersonalizationRepository,
            )
            from agent.src.settings import settings as app_settings

            pref_repo = PersonalizationRepository(app_settings.database_uri)
            user_prefs = await pref_repo.get_preferences(personalization_uid)
            user_memory_enabled = user_prefs.memory_enabled
            if not user_memory_enabled:
                logger.info(
                    "Memory disabled by user preference for %s", personalization_uid
                )
        except Exception:
            logger.debug(
                "Could not load user preferences, using global setting", exc_info=True
            )

    if user_memory_enabled:
        system_prompt = _append_memory_instructions(system_prompt)

    hitl = getattr(resolved_mw, "human_approval", None)
    effects_mode = agent_config.get_effects_mode()

    cache_key = _graph_fingerprint(
        model_name,
        system_prompt,
        [t.name for t in tools],
        hitl_enabled=hitl.enabled if hitl else False,
        hitl_mode=hitl.mode if hitl else "",
        hitl_exclude=hitl.exclude if hitl else [],
        temperature=float(orch_temperature),
        max_tokens=int(orch_max_tokens) if orch_max_tokens else None,
        mcp_names=mcp_server_names or None,
        resource_uris=orchestrator_cfg.get("resources") or None,
        user_identity=str(user_identity or ""),
    )
    now = time.time()
    graph_ttl = float(agent_config.get_cache_config().graph.ttl)
    cached = _graph_cache.get(cache_key)
    build_start_mono = time.monotonic()
    if cached is not None and (now - _graph_cache_ts.get(cache_key, 0)) < graph_ttl:
        age = now - _graph_cache_ts[cache_key]
        logger.warning("Graph cache HIT (age=%.1fs) — skipping rebuild", age)
        _record_build(build_start_mono, cache_hit=True, tools=0)
        return cached

    logger.warning(
        "Graph cache MISS — full rebuild (key=%s, %d cached)",
        cache_key,
        len(_graph_cache),
    )

    if hitl and hitl.enabled:
        from agent.src.agent.config.hitl import denied_tool_names
        from agent.src.infrastructure.middleware import (
            set_policy_denied_tools,
        )

        denied = denied_tool_names(hitl, tools, effects=effects_mode)
        set_policy_denied_tools(denied)
        if denied:
            logger.warning(
                "Denying %d tool(s) by approval policy (effects=%s): %s",
                len(denied),
                effects_mode,
                sorted(denied),
            )
            tools = [t for t in tools if getattr(t, "name", None) not in denied]
            mcp_tools = [t for t in mcp_tools if getattr(t, "name", None) not in denied]

    subagents = load_subagents(tools=mcp_tools)
    backend = get_configured_backend()

    middleware = build_middleware_list(
        resolved_mw,
        model=model,
        model_name=str(model_name or ""),
        backend=backend,
        mcp_tool_names=frozenset(t.name for t in mcp_tools)
        | frozenset(t.name for t in resource_tools),
    )
    from agent.src.attachments.config import AttachmentsConfig
    from agent.src.attachments.middleware import build_attachment_middleware

    try:
        mount = AttachmentsConfig(
            **(agent_config.get_raw_section("attachments") or {})
            if hasattr(agent_config, "get_raw_section")
            else {}
        ).mount_path
    except Exception:
        mount = AttachmentsConfig().mount_path
    middleware.append(build_attachment_middleware(mount))

    from agent.src.self_knowledge.middleware import (
        build_self_knowledge_middleware,
    )

    self_knowledge = build_self_knowledge_middleware(
        user_identity if mcp_tools else None,
        model_name=str(model_name or ""),
    )
    if self_knowledge is not None:
        middleware.append(self_knowledge)

    memory = resolve_memory_param(resolved_mw) if user_memory_enabled else None

    if skill_paths and resolved_mw.skills_enabled:
        from agent.src.agent.config.resolver import to_virtual_skill_sources

        skills_param = to_virtual_skill_sources(skill_paths)
    else:
        skills_param = None

    from agent.src.agent.command_middleware import build_command_middleware

    middleware.append(build_command_middleware())

    from agent.src.knowledge.answer_notes_middleware import (
        build_answer_notes_middleware,
    )

    middleware.append(build_answer_notes_middleware())

    from agent.src.knowledge.citation_middleware import (
        build_citation_middleware,
    )

    try:
        _citations = build_citation_middleware(
            config=agent_config.get_knowledge_config()
        )
        if _citations is not None:
            middleware.append(_citations)
    except Exception as error:
        logger.warning("Citations unavailable: %s", error)

    async_mw = build_async_middleware(subagents, providers_config.async_tasks)
    if async_mw is not None:
        middleware.append(async_mw)

    from agent.src.settings import settings as app_settings

    guardrail_cfg = agent_config.get_guardrails_config()
    guardian_active = guardrail_cfg.enabled and bool(app_settings.GUARDIAN_API_BASE)

    if guardian_active:
        from agent.src.guardrails.tool_proxy import wrap_tools

        tools = wrap_tools(tools)
        system_prompt = _append_safety_stop_instruction(system_prompt)

    create_kwargs: dict[str, Any] = {
        "name": agent_name,
        "model": model,
        "system_prompt": system_prompt,
        "skills": skills_param,
        "tools": tools,
        "subagents": subagents,
        "backend": backend,
        "middleware": middleware,
        "memory": memory,
    }

    import inspect

    create_sig = inspect.signature(create_deep_agent)
    if "permissions" in create_sig.parameters:
        try:
            from agent.src.infrastructure.permissions import build_permissions

            permissions = build_permissions(agent_config.get_filesystem_config())
            if permissions:
                create_kwargs["permissions"] = permissions
        except (ImportError, TypeError):
            pass

    if hitl and hitl.enabled and "interrupt_on" in create_sig.parameters:
        try:
            from agent.src.agent.config.hitl import build_interrupt_on

            interrupt_on = build_interrupt_on(hitl, tools, effects=effects_mode)
            if interrupt_on:
                create_kwargs["interrupt_on"] = interrupt_on
            else:
                logger.warning(
                    "HITL is enabled but interrupt_on is empty — "
                    "no tool calls will be interrupted (all tools may be excluded)"
                )
        except ImportError:
            logger.warning(
                "HITL is enabled but hitl module not available — "
                "upgrade deepagents to activate human-in-the-loop approval"
            )

    _inner_graph = create_deep_agent(**create_kwargs)

    compiled: Any = _inner_graph

    from agent.src.pii import get_scrubber

    if get_scrubber() is not None:
        from agent.src.pii.runnable import PIIAwareRunnable

        compiled = PIIAwareRunnable(compiled)
        logger.info("graph_pii_enabled: wrapped with PIIAwareRunnable")

    if guardian_active:
        from agent.aegra.safety import SafetyAwareRunnable

        compiled = SafetyAwareRunnable(compiled, outermost=True)
        logger.info(
            "graph_guardian_enabled: wrapped with SafetyAwareRunnable and GuardianToolProxy"
        )

    try:
        from agent.src.settings import settings as app_settings

        if app_settings.LIFECYCLE_PERSISTENCE_ENABLED:
            from agent.aegra.lifecycle import build_execution_context

            user_id_val = str(user_identity) if user_identity else ""
            assistant_id_val = getattr(runtime, "assistant_id", None) or ""

            _exec_ctx = build_execution_context(
                model_name=model_name,
                config_hash=cache_key,
                assistant_id=assistant_id_val,
                user_id=user_id_val,
                refresh_token=refresh_token,
                mcp_server_names=mcp_server_names,
                orchestrator_config=orchestrator_cfg,
            )

            setattr(compiled, "_lifecycle_enabled", True)
            setattr(compiled, "_lifecycle_config_hash", cache_key)
            setattr(compiled, "_lifecycle_user_id", user_id_val)
            setattr(compiled, "_lifecycle_assistant_id", assistant_id_val)
            setattr(compiled, "_lifecycle_exec_ctx", _exec_ctx)

            logger.debug("Lifecycle persistence enabled")
    except ImportError:
        pass

    _graph_cache[cache_key] = compiled
    _graph_cache_ts[cache_key] = time.time()

    if len(_graph_cache) > _MAX_GRAPH_CACHE_SIZE:
        oldest_key = min(_graph_cache_ts, key=_graph_cache_ts.get)  # type: ignore[arg-type]
        _graph_cache.pop(oldest_key, None)
        _graph_cache_ts.pop(oldest_key, None)

    tool_count = len(tools)
    _record_build(build_start_mono, cache_hit=False, tools=tool_count)
    sub_count = len(subagents) if subagents else 0
    logger.info(
        "Agent ready: %d tool(s), %d subagent(s), %d middleware [%s], mcp_auth=%s",
        tool_count,
        sub_count,
        len(middleware),
        ", ".join(type(m).__name__ for m in middleware),
        bool(sso_token),
    )

    return compiled
