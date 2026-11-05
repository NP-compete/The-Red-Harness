"""Subagent loading from configuration files."""

from copy import deepcopy
from typing import Any, cast

from deepagents import SubAgent
from deepagents.middleware.subagents import CompiledSubAgent
from langchain_core.language_models import BaseChatModel

from agent.src.agent.config import agent_config
from agent.src.agent.config.model import (
    ModelSpec,
    infer_provider,
    parse_model_config,
)
from agent.src.agent.config.resolver import to_virtual_skill_sources
from agent.src.cache.model_cache import get_or_create_model_from_spec
from agent.src.exceptions import LLMError, SubAgentError
from agent.src.infrastructure.middleware import (
    _build_per_tool_limits,
    _build_tool_exclusions,
    _mcp_tool_names_from_tools,
    _profile_excluded_tools,
    build_audit_middleware,
    build_current_datetime_middleware,
    build_opa_middleware,
    build_user_identity_middleware,
)
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

AsyncSubAgent: type[Any] | None
try:
    from deepagents.middleware.async_subagents import (
        AsyncSubAgent as _AsyncSubAgent,
    )

    AsyncSubAgent = _AsyncSubAgent
except ImportError:
    AsyncSubAgent = None

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)

VALID_AGENT_TYPES = ("default", "compiled", "async")


def load_subagents(
    tools: list[Any],
) -> list[Any] | None:
    """Build subagents from pre-loaded configurations."""
    all_subagent_configs: dict[str, dict[str, Any]] = (
        agent_config.get_all_subagent_configs()
    )

    if not all_subagent_configs:
        logger.warning("No subagent configurations found")
        return None

    orchestrator_cfg = agent_config.get_orchestrator_config()

    logger.info(f"Building {len(all_subagent_configs)} subagent(s)")

    subagents_list: list[Any] = []

    for name, declared in all_subagent_configs.items():
        agent_cfg = deepcopy(declared)
        _inherit_from_orchestrator(agent_cfg, orchestrator_cfg, name)
        try:
            sa = _build_single_subagent(name, agent_cfg, tools)
            subagents_list.append(sa)
        except (ValueError, LLMError) as e:
            raise SubAgentError(f"Failed to build subagent '{name}': {e}") from e
        except Exception as e:
            raise SubAgentError(
                f"Unexpected error building subagent '{name}': {e}"
            ) from e

    logger.info(f"Built {len(subagents_list)} subagent(s) successfully")
    return subagents_list


_DEFAULT_FALLBACK_MODEL = settings.FALLBACK_MODEL


def _inherit_from_orchestrator(
    agent_cfg: dict[str, Any],
    orchestrator_cfg: dict[str, Any],
    name: str,
) -> None:
    """Fill in missing model/mcps from the parent orchestrator config."""
    parent_model = orchestrator_cfg.get("model")
    subagent_model = agent_cfg.get("model")

    if not subagent_model:
        if parent_model:
            logger.info(
                "Subagent '%s' inheriting model from orchestrator: %s",
                name,
                parent_model,
            )
            agent_cfg["model"] = parent_model
        else:
            logger.warning(
                "Subagent '%s' has no model and orchestrator has no model — "
                "falling back to default: %s",
                name,
                _DEFAULT_FALLBACK_MODEL,
            )
            agent_cfg["model"] = _DEFAULT_FALLBACK_MODEL
    elif parent_model:
        agent_cfg["model"] = _inject_fallback_if_missing(
            subagent_model, parent_model, name
        )

    if not agent_cfg.get("mcps"):
        parent_mcps = orchestrator_cfg.get("mcps", [])
        if parent_mcps:
            logger.info(
                "Subagent '%s' inheriting %d MCP(s) from orchestrator",
                name,
                len(parent_mcps),
            )
            agent_cfg["mcps"] = list(parent_mcps)

    if "resources" not in agent_cfg:
        parent_resources = orchestrator_cfg.get("resources")
        if parent_resources is not None:
            agent_cfg["resources"] = list(parent_resources)


def _normalize_model_to_dict(
    raw_model: Any,
    strip_fallback: bool = False,
) -> dict[str, Any] | Any:
    """Normalize model config (string or dict) to dict format."""
    if isinstance(raw_model, str):
        return {
            "provider": infer_provider(raw_model).value,
            "name": raw_model,
        }
    elif isinstance(raw_model, dict):
        result = dict(raw_model)
        if strip_fallback and "fallback" in result:
            del result["fallback"]
        return result
    logger.warning(
        "Invalid model config type: %s, letting parse_model_config handle error",
        type(raw_model).__name__,
    )
    return raw_model


def _inject_fallback_if_missing(
    subagent_model: str | dict[str, Any],
    parent_model: str | dict[str, Any],
    name: str,
) -> str | dict[str, Any]:
    """Inject orchestrator model as fallback if subagent model has no fallback."""
    model_dict = _normalize_model_to_dict(subagent_model)
    if not isinstance(model_dict, dict):
        return cast("str | dict[str, Any]", model_dict)

    if "fallback" in model_dict:
        return model_dict

    logger.debug(
        "Subagent '%s' inheriting orchestrator model as fallback: %s",
        name,
        parent_model,
    )

    fallback_dict = _normalize_model_to_dict(parent_model, strip_fallback=True)
    if not isinstance(fallback_dict, dict):
        return model_dict

    model_dict["fallback"] = fallback_dict
    return model_dict


def _create_primary_model(
    spec: ModelSpec,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> BaseChatModel:
    """Create only the primary BaseChatModel from a ModelSpec, without fallback wrapper."""
    primary_spec = ModelSpec(provider=spec.provider, name=spec.name, fallback=None)

    kwargs: dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens

    return get_or_create_model_from_spec(primary_spec, **kwargs)


def _resolve_subagent_model(agent_cfg: dict[str, Any]) -> BaseChatModel:
    """Parse frontmatter model config and return only the primary BaseChatModel."""
    raw_model = agent_cfg.get("model")
    if raw_model is None:
        raise ValueError("missing required 'model' field in frontmatter")

    spec = parse_model_config(raw_model)

    model_params = agent_config.get_model_params(spec.name)
    temp = model_params.get("temperature")
    max_tok = model_params.get("max_tokens")

    return _create_primary_model(
        spec,
        temperature=float(temp) if temp is not None else None,
        max_output_tokens=int(max_tok) if max_tok is not None else None,
    )


def _format_model_log(spec: ModelSpec) -> str:
    """Format model spec for log messages."""
    return spec.display_name()


def _build_fallback_middleware(spec: ModelSpec) -> list[Any]:
    """Build ModelFallbackMiddleware with BaseChatModel if spec has fallback configured."""
    if spec.fallback is None:
        return []

    try:
        from langchain.agents.middleware import ModelFallbackMiddleware
    except ImportError:
        logger.warning(
            "ModelFallbackMiddleware not available, skipping fallback configuration"
        )
        return []

    fallback_model = _create_primary_model(spec.fallback)

    middleware = ModelFallbackMiddleware(fallback_model)
    logger.info(
        "Configured fallback middleware: %s -> %s",
        spec.display_name(),
        spec.fallback.display_name(),
    )
    return [middleware]


def _build_subagent_budget(resolved: Any) -> Any | None:
    """The block and conversation ceilings for one subagent."""
    from agent.src.agent.config.middleware import ToolCallLimitConfig

    config = getattr(resolved, "tool_call_limit", None)
    if not isinstance(config, ToolCallLimitConfig):
        return None
    if config.per_block <= 0 and config.per_thread <= 0:
        return None

    from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

    return BlockBudgetMiddleware(config=config)


def _build_subagent_spend_limit(resolved: Any) -> Any | None:
    """The spending ceiling for one subagent, when one is configured."""
    from agent.src.agent.config.middleware import SpendLimitConfig

    config = getattr(resolved, "spend_limit", None)
    if not isinstance(config, SpendLimitConfig) or not config.enabled:
        return None
    try:
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        return SpendLimitMiddleware(
            warn_at=config.warning(),
            refuse_at=config.ceiling(),
            currency=settings.RATE_CARD_CURRENCY,
        )
    except (TypeError, ValueError) as error:
        logger.error("Subagent spending limit is not usable: %s", error)
        return None


def _subagent_middleware(
    name: str,
    resolved_tools: list[Any],
    fallback_mw: list[Any],
    model_name: str = "",
) -> list[Any] | None:
    """Merge audit + OPA middleware with optional fallback middleware."""
    middleware: list[Any] = []
    audit_mw = build_audit_middleware(
        mcp_tool_names=_mcp_tool_names_from_tools(resolved_tools),
        agent=name,
    )
    if audit_mw is not None:
        middleware.append(audit_mw)
    opa_mw = build_opa_middleware()
    if opa_mw is not None:
        middleware.append(opa_mw)
    identity_mw = build_user_identity_middleware()
    if identity_mw is not None:
        middleware.append(identity_mw)
    datetime_mw = build_current_datetime_middleware()
    if datetime_mw is not None:
        middleware.append(datetime_mw)

    try:
        resolved = agent_config.resolve_agent_middleware("", None)
        per_tool = resolved.tool_call_limit.per_tool
    except Exception:
        resolved, per_tool = None, {}
    middleware.extend(_build_per_tool_limits(per_tool))

    spend = _build_subagent_spend_limit(resolved)
    if spend is not None:
        middleware.append(spend)

    budget = _build_subagent_budget(resolved)
    if budget is not None:
        middleware.append(budget)

    middleware.extend(_build_tool_exclusions(_profile_excluded_tools(model_name)))

    middleware.extend(fallback_mw)
    return middleware or None


def _build_single_subagent(
    name: str,
    agent_cfg: dict[str, Any],
    tools: list[Any],
) -> Any:
    """Build a single subagent from its configuration."""
    agent_type: str = agent_cfg.get("type", "default")
    if agent_type not in VALID_AGENT_TYPES:
        raise ValueError(
            f"Subagent '{name}' has invalid type '{agent_type}'. "
            f"Valid types: {VALID_AGENT_TYPES}"
        )

    if agent_type == "async":
        return _build_async_subagent(name, agent_cfg)
    if agent_type == "compiled":
        return _build_compiled_subagent(name, agent_cfg, tools)
    return _build_default_subagent(name, agent_cfg, tools)


def _filter_tools_by_mcp_names(
    tools: list[Any],
    mcp_names: list[str],
) -> list[Any]:
    """Scope the orchestrator-wide tool pool to this subagent's declared servers."""
    if not mcp_names:
        return tools
    allowed = set(mcp_names)
    return [
        t
        for t in tools
        if (getattr(t, "metadata", None) or {}).get("mcp_server") in allowed
        or not (getattr(t, "metadata", None) or {}).get("mcp_server")
    ]


def _resolve_and_enforce_subagent_tools(
    name: str,
    agent_cfg: dict[str, Any],
    tools: list[Any],
) -> list[Any]:
    """Resolve, manifest-authorize, and enforce this subagent's tool set."""
    from agent.aegra.mcp_resource_tools import get_mcp_resource_tools
    from agent.aegra.mcp_tool_auth import wrap_mcp_tools_for_auth
    from agent.src.capability import (
        enforce_capability,
        resolve_capability_manifest,
    )

    tool_names: list[str] | None = agent_cfg.get("tools")
    mcp_names: list[str] = agent_cfg.get("mcps", [])
    scoped_tools = _filter_tools_by_mcp_names(tools, mcp_names)

    resolved_tools, manifest = resolve_capability_manifest(
        tool_names, scoped_tools, mcp_names, agent_name=name
    )

    resource_tools = wrap_mcp_tools_for_auth(
        get_mcp_resource_tools(
            server_names=agent_cfg.get("mcps") or None,
            allowed_uris=agent_cfg.get("resources") or None,
        )
    )
    if resource_tools:
        manifest = manifest.merged_with(t.name for t in resource_tools)
        resolved_tools = [*resolved_tools, *resource_tools]

    return enforce_capability(resolved_tools, manifest)


def _build_default_subagent(
    name: str,
    agent_cfg: dict[str, Any],
    tools: list[Any],
) -> SubAgent:
    """Build a standard SubAgent (in-process delegation)."""
    if not agent_cfg.get("model"):
        raise ValueError(
            f"Subagent '{name}' is missing required 'model' field in frontmatter"
        )

    spec = parse_model_config(agent_cfg["model"])
    logger.info(
        "Subagent '%s' [default] using model: %s", name, _format_model_log(spec)
    )

    resolved_tools: list[Any] = _resolve_and_enforce_subagent_tools(
        name, agent_cfg, tools
    )

    skill_paths: list[str] = agent_cfg.get("skill_paths", [])

    fallback_mw = _build_fallback_middleware(spec)

    from agent.src.settings import settings as app_settings

    guardrail_cfg = agent_config.get_guardrails_config()
    guardian_active = guardrail_cfg.enabled and bool(app_settings.GUARDIAN_API_BASE)

    if guardian_active:
        from agent.src.guardrails.tool_proxy import wrap_tools

        resolved_tools = wrap_tools(resolved_tools)

    subagent_params: dict[str, Any] = {
        "name": name,
        "model": _resolve_subagent_model(agent_cfg),
        "description": agent_cfg.get("description", ""),
        "system_prompt": agent_cfg.get("body", ""),
    }

    if resolved_tools:
        subagent_params["tools"] = resolved_tools
    if skill_paths:
        subagent_params["skills"] = to_virtual_skill_sources(skill_paths)
    middleware = _subagent_middleware(name, resolved_tools, fallback_mw, spec.name)
    if middleware:
        subagent_params["middleware"] = middleware

    # SubAgent is a TypedDict, so mypy rejects a dict splat; the call is
    # what builds it, and tests patch the name.
    return SubAgent(**subagent_params)  # type: ignore[typeddict-item,no-any-return]


def _build_compiled_subagent(
    name: str,
    agent_cfg: dict[str, Any],
    tools: list[Any],
) -> CompiledSubAgent:
    """Build a CompiledSubAgent (pre-compiled graph as Runnable)."""
    from deepagents import create_deep_agent

    from agent.src.infrastructure.backend import get_configured_backend

    if not agent_cfg.get("model"):
        raise ValueError(
            f"Subagent '{name}' (compiled) is missing required 'model' field"
        )

    spec = parse_model_config(agent_cfg["model"])
    logger.info(
        "Subagent '%s' [compiled] using model: %s", name, _format_model_log(spec)
    )

    resolved_tools: list[Any] = _resolve_and_enforce_subagent_tools(
        name, agent_cfg, tools
    )
    skill_paths: list[str] = agent_cfg.get("skill_paths", [])

    fallback_mw = _build_fallback_middleware(spec)

    from agent.src.settings import settings as app_settings

    guardrail_cfg = agent_config.get_guardrails_config()
    guardian_active = guardrail_cfg.enabled and bool(app_settings.GUARDIAN_API_BASE)

    if guardian_active:
        from agent.src.guardrails.tool_proxy import wrap_tools

        resolved_tools = wrap_tools(resolved_tools)

    create_kwargs = {
        "name": name,
        "model": _resolve_subagent_model(agent_cfg),
        "system_prompt": agent_cfg.get("body", ""),
        "tools": resolved_tools or None,
        "skills": to_virtual_skill_sources(skill_paths) if skill_paths else None,
        "backend": get_configured_backend(),
    }

    middleware = _subagent_middleware(name, resolved_tools, fallback_mw, spec.name)
    if middleware:
        create_kwargs["middleware"] = middleware

    _inner = create_deep_agent(**create_kwargs)

    runnable: Any = _inner

    from agent.src.pii import get_scrubber

    if get_scrubber() is not None:
        from agent.src.pii.runnable import PIIAwareRunnable

        runnable = PIIAwareRunnable(runnable)
        logger.info("subagent '%s' [compiled] wrapped with PIIAwareRunnable", name)

    if guardian_active:
        from agent.aegra.safety import SafetyAwareRunnable

        runnable = SafetyAwareRunnable(runnable)
        logger.info("subagent '%s' [compiled] wrapped with SafetyAwareRunnable", name)

    return CompiledSubAgent(
        name=name,
        description=agent_cfg.get("description", ""),
        runnable=runnable,
    )


def _build_async_subagent(
    name: str,
    agent_cfg: dict[str, Any],
) -> Any:
    """Build an AsyncSubAgent (remote Agent Protocol server)."""
    if AsyncSubAgent is None:
        raise ValueError(
            f"Subagent '{name}' (async) requires deepagents with async support. "
            "Upgrade deepagents or remove this subagent config."
        )

    graph_id: str | None = agent_cfg.get("graph_id")
    if not graph_id:
        raise ValueError(
            f"Subagent '{name}' (async) is missing required 'graph_id' field"
        )

    logger.info(f"Subagent '{name}' [async] connecting to graph: {graph_id}")

    params: dict[str, Any] = {
        "name": name,
        "description": agent_cfg.get("description", ""),
        "graph_id": graph_id,
    }

    url: str | None = agent_cfg.get("url")
    if url:
        params["url"] = url

    headers = _resolve_async_headers(name)
    if headers:
        params["headers"] = headers

    return AsyncSubAgent(**params)


def _resolve_async_headers(name: str) -> dict[str, str] | None:
    """Resolve auth headers for an async subagent from environment."""
    import os

    env_key = f"ASYNC_SUBAGENT_{name.upper().replace('-', '_')}_TOKEN"
    token = os.environ.get(env_key)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return None
