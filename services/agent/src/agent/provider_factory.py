"""Unified LLM provider factory for per-agent model resolution."""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel

from agent.src.agent.config.model import ModelSpec, Provider
from agent.src.agent.llm import _create_vertex_model, _create_vllm_model
from agent.src.settings import settings


def create_model_from_spec(
    spec: ModelSpec,
    *,
    temperature: float = 0.0,
    max_output_tokens: int | None = None,
) -> BaseChatModel:
    """Create a chat model from a :class:`ModelSpec`."""
    tokens = max_output_tokens or settings.MAX_OUTPUT_TOKENS
    primary = _create_by_provider(
        spec.provider, spec.name, temperature=temperature, max_output_tokens=tokens
    )

    if spec.fallback is None:
        return primary

    secondary = _create_by_provider(
        spec.fallback.provider,
        spec.fallback.name,
        temperature=temperature,
        max_output_tokens=tokens,
    )
    return cast("BaseChatModel", primary.with_fallbacks([secondary]))


def _create_by_provider(
    provider: Provider,
    model_name: str,
    *,
    temperature: float,
    max_output_tokens: int,
) -> BaseChatModel:
    """Route model creation to the appropriate backend."""
    if provider == Provider.VERTEX:
        return _create_vertex_model(model_name, temperature, max_output_tokens)
    if provider == Provider.OPENAI:
        return _create_vllm_model(model_name, temperature, max_output_tokens)
    if provider == Provider.MAAS:
        model_name = "/data/" + model_name.lstrip("/").removeprefix("data/")
        return _create_vllm_model(model_name, temperature, max_output_tokens)
    raise ValueError(f"unsupported provider: {provider}")
