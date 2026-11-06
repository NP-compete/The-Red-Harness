"""Response shapes for the handful of routes on the app itself."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class VersionOut(BaseModel):
    """The service and its version."""

    service: str
    version: str


class AgentStructureOut(BaseModel):
    """What this agent is made of, read out of the config tree."""

    model_config = ConfigDict(extra="allow")

    name: str
    orchestrator: dict[str, Any]
    subagents: dict[str, dict[str, Any]]
    mcp_servers: dict[str, Any]
    available_skills: list[str]


class HealthProbeOut(BaseModel):
    """What `/healthz`, `/livez` and `/readyz` answer."""

    model_config = ConfigDict(extra="allow")

    status: str
    version: str = ""
    uptime_seconds: float | None = None
    checks: dict[str, Any] | None = None
