"""Model configuration types for per-agent LLM provider selection."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator

from agent.src.agent.llm import is_openai_model, is_vertex_model


class Provider(str, Enum):
    """Supported LLM provider backends."""

    VERTEX = "vertex"
    OPENAI = "openai"
    MAAS = "maas"


class ModelSpec(BaseModel):
    """Resolved model configuration with optional fallback."""

    provider: Provider
    name: str
    fallback: ModelSpec | None = None

    @model_validator(mode="after")
    def _validate_name(self) -> ModelSpec:
        if not self.name or not self.name.strip():
            raise ValueError("model name cannot be empty")
        return self

    def display_name(self) -> str:
        """Human-readable model identifier for logging."""
        base = f"{self.provider.value}:{self.name}"
        if self.fallback:
            return f"{base} (fallback: {self.fallback.display_name()})"
        return base


def infer_provider(model_name: str) -> Provider:
    """Infer provider from a legacy model name string."""
    if is_vertex_model(model_name):
        return Provider.VERTEX
    if is_openai_model(model_name):
        return Provider.OPENAI
    return Provider.MAAS


def _model_override() -> str | None:
    """Read MODEL_OVERRIDE at call time, not import time."""
    from agent.src.settings import settings

    value = getattr(settings, "MODEL_OVERRIDE", None)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def parse_model_config(raw: str | dict[str, Any]) -> ModelSpec:
    """Parse a frontmatter ``model`` field into a :class:`ModelSpec`."""
    override = _model_override()
    if override is not None:
        return ModelSpec(provider=infer_provider(override), name=override)

    if isinstance(raw, str):
        name = raw.strip()
        if not name:
            raise ValueError("model name cannot be empty")
        return ModelSpec(provider=infer_provider(name), name=name)

    if not isinstance(raw, dict):
        raise TypeError(f"model config must be str or dict, got {type(raw).__name__}")

    allowed_keys = {"provider", "name", "fallback"}
    unknown = set(raw.keys()) - allowed_keys
    if unknown:
        raise ValueError(
            f"unknown model config keys: {sorted(unknown)}; "
            f"allowed: {sorted(allowed_keys)}"
        )

    name_raw = raw.get("name")
    if not isinstance(name_raw, str) or not name_raw.strip():
        raise ValueError("model config object requires non-empty 'name'")
    name = name_raw.strip()

    provider_raw = raw.get("provider")
    if provider_raw is None:
        provider = infer_provider(name)
    else:
        try:
            provider = Provider(provider_raw)
        except ValueError as e:
            raise ValueError(
                f"invalid provider '{provider_raw}'; "
                f"must be one of: {[p.value for p in Provider]}"
            ) from e

    fallback_raw = raw.get("fallback")
    fallback: ModelSpec | None = None
    if fallback_raw is not None:
        if not isinstance(fallback_raw, dict):
            raise ValueError("model fallback must be an object")
        if "fallback" in fallback_raw:
            raise ValueError("nested fallback chains are not supported")
        fallback = parse_model_config(fallback_raw)

    return ModelSpec(
        provider=provider,
        name=str(name).strip(),
        fallback=fallback,
    )


def model_spec_cache_key(spec: ModelSpec) -> str:
    """Stable cache identity string for a model spec including fallback."""
    parts = [f"{spec.provider.value}:{spec.name}"]
    if spec.fallback:
        parts.append(f"→{model_spec_cache_key(spec.fallback)}")
    return "".join(parts)
