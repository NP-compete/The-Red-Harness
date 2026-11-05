"""Cache warming — pre-populate caches at startup."""

from agent.src.cache.config import cache_settings
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def warm_caches() -> dict[str, bool]:
    """Pre-populate caches. Returns a status dict per cache layer."""
    results: dict[str, bool] = {}

    if not cache_settings.is_enabled("warming"):
        logger.debug("Cache warming disabled — skipping")
        return results

    logger.info("Warming caches...")

    results["models"] = _warm_models()

    logger.info("Cache warming complete: %s", results)
    return results


def _warm_models() -> bool:
    """Pre-create LLM model instances for orchestrator + subagents."""
    if not cache_settings.is_enabled("model"):
        return False

    try:
        from agent.src.agent.config import agent_config
        from agent.src.agent.config.model import parse_model_config
        from agent.src.cache.model_cache import get_or_create_model_from_spec

        orch = agent_config.get_orchestrator_config()
        orch_model = orch.get("model", settings.DEFAULT_MODEL)

        orch_spec = parse_model_config(orch_model)
        get_or_create_model_from_spec(orch_spec)
        logger.info(
            "Warmed orchestrator model: %s (provider: %s)",
            orch_spec.name,
            orch_spec.provider.value,
        )

        for name, cfg in agent_config.get_all_subagent_configs().items():
            sub_model = cfg.get("model")
            if sub_model:
                spec = parse_model_config(sub_model)
                get_or_create_model_from_spec(spec)
                logger.info("Warmed subagent '%s' model: %s", name, spec.display_name())

        return True
    except Exception:
        logger.warning("Model cache warming failed", exc_info=True)
        return False
