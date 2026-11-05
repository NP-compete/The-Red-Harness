"""Named ways of answering, over routing that already exists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_DEFAULT_MULTIPLIER = 1.0


@dataclass(frozen=True)
class Profile:
    """One named way of answering, already resolved to a model."""

    name: str
    tier: str
    model: str
    effort: str
    budget_multiplier: float


def _models_by_tier(config: Any) -> dict[str, str]:
    """The model configured for each tier."""
    tiers = config.get("tiers") if isinstance(config, dict) else None
    if not isinstance(tiers, list):
        return {}
    found: dict[str, str] = {}
    for tier in tiers:
        if isinstance(tier, dict) and tier.get("name"):
            found[str(tier["name"])] = str(tier.get("model", ""))
    return found


def profiles_from(config: Any) -> list[Profile]:
    """Every declared profile that names a tier this deployment has."""
    try:
        if not isinstance(config, dict):
            return []
        declared = config.get("profiles")
        if not isinstance(declared, list):
            return []

        routing_on = bool(config.get("enabled", False))
        declared_models = _models_by_tier(config)
        models = declared_models if routing_on else dict.fromkeys(declared_models, "")
        found: list[Profile] = []
        for entry in declared:
            if not isinstance(entry, dict):
                continue
            name, tier = str(entry.get("name", "")), str(entry.get("tier", ""))
            if not name or tier not in models:
                continue
            try:
                multiplier = float(entry.get("budget_multiplier", _DEFAULT_MULTIPLIER))
            except (TypeError, ValueError):
                multiplier = _DEFAULT_MULTIPLIER
            found.append(
                Profile(
                    name=name,
                    tier=tier,
                    model=models[tier],
                    effort=str(entry.get("effort", "")),
                    budget_multiplier=multiplier,
                )
            )
        return found
    except Exception:
        logger.debug("Could not read the reasoning profiles", exc_info=True)
        return []


def distinguishable(profiles: list[Profile]) -> bool:
    """Whether picking between these would send a different request."""
    shapes = {(one.model, one.effort) for one in profiles}
    return len(shapes) > 1


def profile_named(profiles: list[Profile], name: str) -> Profile | None:
    """The profile called `name`, or `None` if there is none."""
    for one in profiles:
        if one.name == name:
            return one
    return None


def effort_reaches_the_model(model: str) -> bool:
    """Whether asking this model to think harder changes the request."""
    from agent.src.settings import settings

    if settings.MODEL_OVERRIDE or settings.VLLM_BASE_URL:
        return False
    return model.strip().lower().startswith("gemini-")


def worth_offering(config: Any) -> list[Profile]:
    """The profiles to put on screen, or nothing."""
    found = profiles_from(config)
    if not distinguishable(found):
        return []
    if len({one.model for one in found if one.model}) > 1:
        return found
    return found if effort_reaches_the_model(_model_in_use(found)) else []


def _model_in_use(profiles: list[Profile]) -> str:
    """Which model the effort would actually be applied to."""
    for one in profiles:
        if one.model:
            return one.model
    try:
        from agent.src.agent.config import agent_config

        declared = (agent_config.get_orchestrator_config() or {}).get("model")
        if isinstance(declared, dict):
            return str(declared.get("name") or "")
        return str(declared or "")
    except Exception:  # noqa: BLE001
        logger.debug("Could not read the agent's model", exc_info=True)
        return ""


_BUDGETS = {"low": 0, "medium": 1024, "high": 4096}


def budget_for_effort(effort: object) -> int | None:
    """Reasoning tokens for this effort, or nothing to leave it alone."""
    if not isinstance(effort, str):
        return None
    return _BUDGETS.get(effort.strip().lower())
