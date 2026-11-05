"""PII middleware configuration models."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    """PII handling strategy."""

    scrub = "scrub"
    tokenize = "tokenize"
    hash = "hash"
    redact = "redact"
    mask = "mask"
    block = "block"


class PIIRule(BaseModel):
    """Single PII detection rule with strategy and provider."""

    name: str
    regex: Optional[str] = None
    strategy: ActionType = ActionType.scrub
    provider: Literal["regex", "presidio", "custom", "default"] = "regex"
    label: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: dict) -> dict:
        if "action" in data and "strategy" not in data:
            data["strategy"] = data.pop("action")
        if "detector" in data and "provider" not in data:
            data["provider"] = data.pop("detector")
        data.pop("pattern_type", None)
        return data

    @property
    def action(self) -> ActionType:
        """Backwards-compatible alias."""
        return self.strategy

    @property
    def detector(self) -> str:
        """Backwards-compatible alias."""
        return self.provider

    @property
    def pattern_type(self) -> str:
        """Backwards-compatible alias — 'custom' if regex provided, else 'builtin'."""
        return "custom" if self.regex else "builtin"

    def effective_label(self) -> str:
        """Return the label used in token placeholders."""
        return (self.label or self.name).upper()


class PIIConfig(BaseModel):
    """Top-level PII middleware configuration."""

    enabled: bool = False
    trace_strategy: Literal["redact", "hash"] = "hash"
    rules: list[PIIRule] = Field(default_factory=list)
