"""LLM model instance cache."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from cachetools import TTLCache

from agent.src.agent.config.model import ModelSpec, model_spec_cache_key
from agent.src.cache import metrics
from agent.src.cache.config import cache_settings
from agent.utils.pylogger import get_python_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from langchain_core.language_models import BaseChatModel

logger = get_python_logger()

_LegacyCacheKey = tuple[str, float, int]
_SpecCacheKey = tuple[str, float, int]

_lock = threading.Lock()
_legacy_cache: TTLCache[_LegacyCacheKey, BaseChatModel] | None = None
_spec_cache: TTLCache[_SpecCacheKey, BaseChatModel] | None = None


def _get_legacy_cache() -> TTLCache[_LegacyCacheKey, BaseChatModel]:
    global _legacy_cache  # noqa: PLW0603
    if _legacy_cache is None:
        _legacy_cache = TTLCache(
            maxsize=cache_settings.CACHE_MODEL_MAX_SIZE,
            ttl=cache_settings.CACHE_MODEL_TTL,
        )
    return _legacy_cache


def _get_spec_cache() -> TTLCache[_SpecCacheKey, BaseChatModel]:
    global _spec_cache  # noqa: PLW0603
    if _spec_cache is None:
        _spec_cache = TTLCache(
            maxsize=cache_settings.CACHE_MODEL_MAX_SIZE,
            ttl=cache_settings.CACHE_MODEL_TTL,
        )
    return _spec_cache


def _get_cache() -> TTLCache[_LegacyCacheKey, BaseChatModel]:
    """Backward-compatible alias for legacy cache getter."""
    return _get_legacy_cache()


def get_or_create_model(
    model_name: str,
    temperature: float = 0.0,
    max_output_tokens: int | None = None,
) -> "BaseChatModel":
    """Return a cached model or create a new one."""
    from agent.src.agent.llm import create_model
    from agent.src.settings import settings

    tokens = max_output_tokens or settings.MAX_OUTPUT_TOKENS

    if not cache_settings.is_enabled("model"):
        return create_model(model_name, temperature, tokens)

    key: _LegacyCacheKey = (model_name, temperature, tokens)

    with _lock:
        cache = _get_legacy_cache()
        model = cache.get(key)
        if model is not None:
            metrics.record_hit("model")
            logger.debug("Model cache HIT: %s", model_name)
            return model

    metrics.record_miss("model")
    logger.debug("Model cache MISS: %s — creating", model_name)
    model = create_model(model_name, temperature, tokens)

    with _lock:
        cache = _get_legacy_cache()
        cache[key] = model
        metrics.record_set("model")

    return model


def get_or_create_model_from_spec(
    spec: ModelSpec,
    temperature: float = 0.0,
    max_output_tokens: int | None = None,
) -> BaseChatModel:
    """Return a cached model for a :class:`ModelSpec` or create a new one."""
    from agent.src.agent.provider_factory import create_model_from_spec
    from agent.src.settings import settings

    tokens = max_output_tokens or settings.MAX_OUTPUT_TOKENS
    cache_id = model_spec_cache_key(spec)

    if not cache_settings.is_enabled("model"):
        return create_model_from_spec(
            spec, temperature=temperature, max_output_tokens=tokens
        )

    key: _SpecCacheKey = (cache_id, temperature, tokens)

    with _lock:
        cache = _get_spec_cache()
        model = cache.get(key)
        if model is not None:
            metrics.record_hit("model")
            logger.debug("Model cache HIT: %s", cache_id)
            return model

    metrics.record_miss("model")
    logger.debug("Model cache MISS: %s — creating", cache_id)
    model = create_model_from_spec(
        spec, temperature=temperature, max_output_tokens=tokens
    )

    with _lock:
        cache = _get_spec_cache()
        cache[key] = model
        metrics.record_set("model")

    return model


def invalidate(model_name: str | None = None) -> None:
    """Drop cached model(s)."""
    with _lock:
        legacy = _get_legacy_cache()
        spec = _get_spec_cache()
        if model_name is None:
            legacy.clear()
            spec.clear()
            logger.info("Model cache cleared")
            return
        keys_to_remove = [k for k in legacy if k[0] == model_name]
        for k in keys_to_remove:
            del legacy[k]
        if keys_to_remove:
            logger.info(
                "Model cache: evicted %d legacy entry(s) for '%s'",
                len(keys_to_remove),
                model_name,
            )


def cached_count() -> int:
    """Return the number of currently cached models (legacy + spec)."""
    with _lock:
        return len(_get_legacy_cache()) + len(_get_spec_cache())
