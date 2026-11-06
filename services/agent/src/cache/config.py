"""Cache configuration with feature flags."""

from pydantic import Field
from pydantic_settings import BaseSettings


class CacheSettings(BaseSettings):
    """Feature-flagged cache configuration loaded from environment."""

    CACHE_ENABLED: bool = Field(default=False)

    CACHE_MODEL_ENABLED: bool = Field(default=False)
    CACHE_MODEL_TTL: int = Field(default=600, ge=10, le=7200)
    CACHE_MODEL_MAX_SIZE: int = Field(default=10, ge=1, le=100)

    CACHE_PERSONALIZATION_ENABLED: bool = Field(default=False)
    CACHE_PERSONALIZATION_TTL: int = Field(default=120, ge=10, le=3600)

    CACHE_METRICS_ENABLED: bool = Field(default=False)
    CACHE_WARMING_ENABLED: bool = Field(default=False)
    CACHE_REDIS_ENABLED: bool = Field(default=False)

    def is_enabled(self, layer: str) -> bool:
        """Check if a specific cache layer is active."""
        if not self.CACHE_ENABLED:
            return False
        flag = getattr(self, f"CACHE_{layer.upper()}_ENABLED", False)
        return bool(flag)


cache_settings = CacheSettings()
