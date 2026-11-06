"""Middleware configuration models and resolution logic."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


class SummarizationToolConfig(BaseModel):
    """Config for SummarizationToolMiddleware."""

    enabled: bool = True


class ApprovalPolicy(BaseModel):
    """What to do when a matching tool is about to run."""

    tools: list[str] = Field(default_factory=list)
    decision: Literal["allow", "ask", "deny"] = "ask"

    risk: Literal["low", "medium", "high"] = "medium"

    reason: str = ""


class ExecutionConfig(BaseModel):
    """What a run is allowed to actually do."""

    effects: Literal["live", "dry_run"] = "live"


class HumanApprovalConfig(BaseModel):
    """Config for human-in-the-loop tool approval."""

    enabled: bool = True
    mode: Literal["all", "none"] = "all"

    exclude: list[str] = Field(default_factory=list)

    policies: list[ApprovalPolicy] = Field(default_factory=list)

    default_decision: Literal["allow", "ask", "deny"] = "ask"


class MemoryConfig(BaseModel):
    """Config for MemoryMiddleware (activated via memory= param)."""

    enabled: bool = True
    namespaces: list[str] = Field(default_factory=lambda: ["memories"])


class PatchToolCallsConfig(BaseModel):
    """Config for PatchToolCallsMiddleware (auto-included by deepagents)."""

    enabled: bool = True


class SkillsConfig(BaseModel):
    """Config for SkillsMiddleware (auto-included when skills= provided)."""

    enabled: bool = True


class ModelCallLimitConfig(BaseModel):
    """Config for ModelCallLimitMiddleware — cap LLM calls per run."""

    enabled: bool = True
    run_limit: int = 50


class ToolExclusionConfig(BaseModel):
    """Tools removed by product decision, not by model capability."""

    enabled: bool = True
    tools: list[str] = Field(default_factory=list)


class SpendLimitConfig(BaseModel):
    """A ceiling on what one run may cost, in the rate card's currency."""

    warn_at: str = ""
    refuse_at: str = ""

    @property
    def enabled(self) -> bool:
        """Whether this deployment set either threshold."""
        return bool(self.warn_at or self.refuse_at)

    def _amount(self, raw: str) -> Decimal | None:
        if not raw.strip():
            return None
        try:
            return Decimal(raw.strip())
        except InvalidOperation as error:
            raise ValueError(f"'{raw}' is not a usable amount") from error

    def warning(self) -> Decimal | None:
        """The amount to warn at, or nothing."""
        return self._amount(self.warn_at)

    def ceiling(self) -> Decimal | None:
        """The amount to refuse at, or nothing."""
        return self._amount(self.refuse_at)


class ToolShortlistConfig(BaseModel):
    """Which tools a turn sends to the model."""

    strategy: Literal["none", "static", "embedding"] = "none"
    max_tools: int = Field(default=40, ge=0)
    always_include: list[str] = Field(default_factory=list)
    embedding_model: str = ""


class CompactionConfig(BaseModel):
    """When a long conversation is summarised, and how much survives."""

    trigger_fraction: float | None = Field(default=None, gt=0, le=1)
    keep_messages: int | None = Field(default=None, ge=1)

    @property
    def configured(self) -> bool:
        """Whether a deployment asked for compaction at all."""
        return self.trigger_fraction is not None or self.keep_messages is not None

    def trigger(self) -> tuple[str, float] | None:
        """When to compact, as the pair the middleware takes."""
        if self.trigger_fraction is None:
            return None
        return ("fraction", self.trigger_fraction)

    def keep(self) -> tuple[str, int] | None:
        """How much to keep, as the pair the middleware takes."""
        if self.keep_messages is None:
            return None
        return ("messages", self.keep_messages)


class ToolCallLimitConfig(BaseModel):
    """Config for ToolCallLimitMiddleware — cap tool calls per run."""

    enabled: bool = True
    run_limit: int = 200
    per_tool: dict[str, int] = Field(default_factory=dict)
    per_block: int = Field(default=0, ge=0)
    per_thread: int = Field(default=0, ge=0)
    on_exceeded: Literal["exclude", "error"] = "exclude"


class ModelRetryConfig(BaseModel):
    """Config for ModelRetryMiddleware — retry on transient failures."""

    enabled: bool = True
    max_retries: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0


class ModelFallbackConfig(BaseModel):
    """Config for ModelFallbackMiddleware — switch to backup model."""

    enabled: bool = False
    fallback_model: str = ""


class ToolRetryConfig(BaseModel):
    """Config for ToolRetryMiddleware — retry specific tools."""

    enabled: bool = False
    max_retries: int = 2
    tools: list[str] = Field(default_factory=list)


class PIIRule(BaseModel):
    """A single PII rule — provider determines which backend handles it."""

    name: str
    strategy: str = "redact"
    provider: Literal["regex", "presidio", "custom", "default"] = "default"
    regex: str | None = None
    label: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: dict) -> dict:
        if "type" in data and "name" not in data:
            data["name"] = data.pop("type")
        return data


class PIIConfig(BaseModel):
    """Unified PII config — all rules in one place, provider routes each rule."""

    enabled: bool = False
    trace_strategy: Literal["redact", "hash"] = "hash"
    rules: list[PIIRule] = Field(default_factory=list)


class ToolOutputConfig(BaseModel):
    """How tool results are treated."""

    trusted_servers: list[str] = Field(default_factory=list)


class MiddlewareDefaults(BaseModel):
    """Global middleware defaults from agent.yaml."""

    summarization_tool: SummarizationToolConfig = Field(
        default_factory=SummarizationToolConfig
    )
    human_approval: HumanApprovalConfig = Field(default_factory=HumanApprovalConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    patch_tool_calls: PatchToolCallsConfig = Field(default_factory=PatchToolCallsConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    model_call_limit: ModelCallLimitConfig = Field(default_factory=ModelCallLimitConfig)
    tool_call_limit: ToolCallLimitConfig = Field(default_factory=ToolCallLimitConfig)
    tool_exclusion: ToolExclusionConfig = Field(default_factory=ToolExclusionConfig)
    model_retry: ModelRetryConfig = Field(default_factory=ModelRetryConfig)
    model_fallback: ModelFallbackConfig = Field(default_factory=ModelFallbackConfig)
    tool_retry: ToolRetryConfig = Field(default_factory=ToolRetryConfig)
    tool_output: ToolOutputConfig = Field(default_factory=ToolOutputConfig)
    spend_limit: SpendLimitConfig = Field(default_factory=SpendLimitConfig)
    compaction: CompactionConfig = Field(default_factory=CompactionConfig)
    tool_shortlist: ToolShortlistConfig = Field(default_factory=ToolShortlistConfig)
    extra: list[Any] = Field(default_factory=list)


class ProfileConfig(BaseModel):
    """Per-model profile configuration for HarnessProfile registration."""

    excluded_middleware: list[str] = Field(default_factory=list)
    excluded_tools: list[str] = Field(default_factory=list)
    system_prompt_suffix: str = ""
    general_purpose_subagent: dict[str, Any] = Field(default_factory=dict)


class MiddlewareFileConfig(BaseModel):
    """Structure of the middleware + harness_profiles sections in runtime/agent.yaml."""

    defaults: MiddlewareDefaults = Field(default_factory=MiddlewareDefaults)
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)


class ResolvedMiddlewareConfig(BaseModel):
    """Final resolved config for a single agent after merge."""

    summarization_tool_enabled: bool = True
    human_approval: HumanApprovalConfig = Field(default_factory=HumanApprovalConfig)
    memory_enabled: bool = True
    memory_namespaces: list[str] = Field(default_factory=lambda: ["memories"])
    patch_tool_calls_enabled: bool = True
    skills_enabled: bool = True
    model_call_limit: ModelCallLimitConfig = Field(default_factory=ModelCallLimitConfig)
    tool_call_limit: ToolCallLimitConfig = Field(default_factory=ToolCallLimitConfig)
    tool_exclusion: ToolExclusionConfig = Field(default_factory=ToolExclusionConfig)
    model_retry: ModelRetryConfig = Field(default_factory=ModelRetryConfig)
    model_fallback: ModelFallbackConfig = Field(default_factory=ModelFallbackConfig)
    tool_retry: ToolRetryConfig = Field(default_factory=ToolRetryConfig)
    tool_output: ToolOutputConfig = Field(default_factory=ToolOutputConfig)
    spend_limit: SpendLimitConfig = Field(default_factory=SpendLimitConfig)
    compaction: CompactionConfig = Field(default_factory=CompactionConfig)
    tool_shortlist: ToolShortlistConfig = Field(default_factory=ToolShortlistConfig)
    extra_middleware: list[Any] = Field(default_factory=list)
    excluded_middleware: list[str] = Field(default_factory=list)


def _sections(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept either a standalone file or an agent file."""
    if "defaults" in raw or "profiles" in raw:
        return raw
    return {
        "defaults": raw.get("middleware", {}),
        "profiles": raw.get("harness_profiles", {}),
    }


def load_middleware_config(config_path: Path) -> MiddlewareFileConfig:
    """Load and validate middleware.yaml from disk."""
    if not config_path.is_file():
        logger.info("No middleware.yaml found — using defaults")
        return MiddlewareFileConfig()

    try:
        raw = yaml.safe_load(config_path.read_text()) or {}
        config: MiddlewareFileConfig = MiddlewareFileConfig.model_validate(
            _sections(raw)
        )
        logger.info("Loaded middleware config: %d profile(s)", len(config.profiles))
        return config
    except Exception as e:
        logger.warning("Failed to parse middleware.yaml, using defaults: %s", e)
        return MiddlewareFileConfig()


def resolve_middleware(
    file_config: MiddlewareFileConfig,
    model_name: str,
    agent_overrides: dict[str, Any] | None = None,
) -> ResolvedMiddlewareConfig:
    """Resolve final middleware config for an agent."""
    defaults = file_config.defaults
    profile = file_config.profiles.get(model_name, ProfileConfig())
    overrides = agent_overrides or {}

    summarization_enabled = _resolve_bool(
        defaults.summarization_tool.enabled,
        overrides.get("summarization_tool"),
    )
    memory_enabled = _resolve_bool(
        defaults.memory.enabled,
        overrides.get("memory"),
    )
    patch_enabled = _resolve_bool(
        defaults.patch_tool_calls.enabled,
        overrides.get("patch_tool_calls"),
    )
    skills_enabled = _resolve_bool(
        defaults.skills.enabled,
        overrides.get("skills"),
    )

    memory_namespaces = defaults.memory.namespaces
    if isinstance(overrides.get("memory"), dict):
        memory_namespaces = overrides["memory"].get("namespaces", memory_namespaces)

    extra = list(defaults.extra)
    if "extra" in overrides:
        extra.extend(overrides["extra"])

    if "patch_tool_calls" in profile.excluded_middleware:
        patch_enabled = False

    tool_output = defaults.tool_output
    if isinstance(overrides.get("tool_output"), dict):
        tool_output = ToolOutputConfig.model_validate(overrides["tool_output"])

    human_approval = defaults.human_approval
    if isinstance(overrides.get("human_approval"), dict):
        human_approval = HumanApprovalConfig.model_validate(overrides["human_approval"])
    elif isinstance(overrides.get("human_approval"), bool):
        human_approval = HumanApprovalConfig(enabled=overrides["human_approval"])

    return ResolvedMiddlewareConfig(
        summarization_tool_enabled=summarization_enabled,
        human_approval=human_approval,
        memory_enabled=memory_enabled,
        memory_namespaces=memory_namespaces,
        patch_tool_calls_enabled=patch_enabled,
        skills_enabled=skills_enabled,
        model_call_limit=defaults.model_call_limit,
        tool_call_limit=defaults.tool_call_limit,
        tool_exclusion=defaults.tool_exclusion,
        model_retry=defaults.model_retry,
        model_fallback=defaults.model_fallback,
        tool_retry=defaults.tool_retry,
        tool_output=tool_output,
        spend_limit=defaults.spend_limit,
        compaction=defaults.compaction,
        tool_shortlist=defaults.tool_shortlist,
        extra_middleware=extra,
        excluded_middleware=profile.excluded_middleware,
    )


def _resolve_bool(default: bool, override: Any) -> bool:
    """Resolve a boolean config with potential override."""
    if override is None:
        return default
    if isinstance(override, bool):
        return override
    if isinstance(override, dict):
        return bool(override.get("enabled", default))
    return default
