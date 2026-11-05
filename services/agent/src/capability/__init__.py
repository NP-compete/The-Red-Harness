"""Capability model — enforced tool-invocation manifest independent of the agent prompt."""

from agent.src.capability.manifest import (
    CapabilityManifest,
    resolve_capability_manifest,
)
from agent.src.capability.tool_proxy import CapabilityToolProxy, enforce_capability

__all__ = [
    "CapabilityManifest",
    "resolve_capability_manifest",
    "CapabilityToolProxy",
    "enforce_capability",
]
