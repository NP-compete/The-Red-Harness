"""Channel configuration, loaded from `config/agent/integrations/channels.yaml`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class IdentityConfig(BaseModel):
    """How a channel sender becomes a platform user."""

    map: dict[str, str] = Field(default_factory=dict)

    default_user: str | None = None

    def resolve(self, sender: str) -> str | None:
        """Platform user for this sender, or None if they are not allowed."""
        return self.map.get(sender) or self.default_user


class ChannelConfig(BaseModel):
    """One inbound channel."""

    type: Literal["slack", "webhook"]
    enabled: bool = True

    signing_secret_env: str

    max_age_seconds: int = Field(default=300, ge=1, le=3600)

    identity: IdentityConfig = Field(default_factory=IdentityConfig)

    assistant_id: str = "agent"

    timeout_seconds: int = Field(default=300, ge=5, le=3600)

    @property
    def signing_secret(self) -> str | None:
        """The secret, read at use time so rotation does not need a restart."""
        from agent.src.security.secret_source import SecretUnavailable, resolve

        try:
            return resolve(self.signing_secret_env)
        except SecretUnavailable:
            return None


class ChannelsFileConfig(BaseModel):
    """The whole channels.yaml."""

    enabled: bool = False
    channels: dict[str, ChannelConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_enabled_channels_are_usable(self) -> ChannelsFileConfig:
        if not self.enabled:
            return self
        active = [name for name, c in self.channels.items() if c.enabled]
        if not active:
            raise ValueError(
                "channels.enabled is true but no channel is enabled; "
                "either enable one or set channels.enabled to false"
            )
        return self

    def active(self) -> dict[str, ChannelConfig]:
        """Enabled channels, empty when the feature is off."""
        if not self.enabled:
            return {}
        return {name: c for name, c in self.channels.items() if c.enabled}
