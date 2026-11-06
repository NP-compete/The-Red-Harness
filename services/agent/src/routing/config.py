"""Model router configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from agent._root import CONFIG_ROOT
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


class ModelTier(BaseModel):
    """One routable model and the work it should absorb."""

    name: str
    model: str
    criteria: str
    max_output_tokens: int | None = None


class RouterConfig(BaseModel):
    """Parsed ``router.yaml``."""

    enabled: bool = False

    strategy: Literal["first_message", "every_turn"] = "first_message"

    tiers: list[ModelTier] = Field(default_factory=list)

    profiles: list[dict[str, object]] = Field(default_factory=list)

    fallback_tier: str | None = None

    classifier_model: str = ""
    classifier_timeout: float = 10.0

    def tier_by_name(self, name: str) -> ModelTier | None:
        """The tier with this name, or None when nothing matches."""
        for tier in self.tiers:
            if tier.name == name:
                return tier
        return None

    @property
    def default_tier(self) -> ModelTier | None:
        """Where to land when classification cannot be trusted."""
        if self.fallback_tier:
            explicit = self.tier_by_name(self.fallback_tier)
            if explicit:
                return explicit
        return self.tiers[-1] if self.tiers else None

    def model_post_init(self, _context: object) -> None:
        """Reject a routing config that cannot route: enabled needs two tiers."""
        if not self.enabled:
            return
        if len(self.tiers) < 2:
            raise ValueError("router requires at least two tiers to route between")
        if self.fallback_tier and not self.tier_by_name(self.fallback_tier):
            raise ValueError(
                f"fallback_tier '{self.fallback_tier}' is not a defined tier"
            )
        names = [t.name for t in self.tiers]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate tier names: {names}")


def _candidate_paths() -> list[Path]:
    explicit = os.getenv("ROUTER_CONFIG_PATH")
    agent_dir = Path(
        os.getenv(
            "CONFIG_PATH",
            str(CONFIG_ROOT),
        )
    )
    candidates = [
        agent_dir / "runtime" / "router.yaml",
        agent_dir.parent / "routing" / "router.yaml",
    ]
    if explicit:
        candidates.insert(0, Path(explicit))
    return candidates


def load_router_config(path: Path | None = None) -> RouterConfig:
    """Load ``router.yaml``; absent means routing is off."""
    if path is not None:
        found: Path | None = path if path.is_file() else None
    else:
        found = next((p for p in _candidate_paths() if p.is_file()), None)

    if found is None:
        return RouterConfig(enabled=False)

    with found.open() as handle:
        raw = yaml.safe_load(handle) or {}

    config = RouterConfig(**raw)
    if config.enabled:
        logger.info(
            "Model router enabled: %d tier(s), strategy=%s",
            len(config.tiers),
            config.strategy,
        )
    return config
