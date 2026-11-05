"""What is actually true of a deployment, asked from outside it."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

TIMEOUT_SECONDS = 3.0

MODEL_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_APPLICATION_CREDENTIALS_CONTENT",
    "VERTEX_PROJECT",
)


def _get(url: str) -> tuple[int, Any]:
    """GET `url` and return the status and decoded body."""
    import httpx

    response = httpx.get(url, timeout=TIMEOUT_SECONDS)
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, {}


def agent_reachable(base_url: str) -> bool:
    """Whether the agent answers its health check."""
    try:
        return _get(f"{base_url}/health")[0] == 200
    except Exception:
        return False


def config_clean(base_url: str) -> bool | None:
    """Whether the agent's configuration loaded without problems."""
    try:
        status, payload = _get(f"{base_url}/admin/config/problems")
    except Exception:
        return None
    if status != 200 or not isinstance(payload, dict) or "clean" not in payload:
        return None
    return bool(payload["clean"])


def within_limits(base_url: str) -> bool | None:
    """Whether anything is over a configured threshold."""
    try:
        status, payload = _get(f"{base_url}/analytics/alerts")
    except Exception:
        return None
    if status != 200 or not isinstance(payload, dict) or "ok" not in payload:
        return None
    return bool(payload["ok"])


def config_readable() -> bool:
    """Whether the configuration tree is there and can be read."""
    path = Path(os.environ.get("CONFIG_PATH", "config/agent"))
    try:
        return path.is_dir() and any(path.iterdir())
    except Exception:
        return False


def model_key_present() -> bool:
    """Whether any provider credential is set."""
    return any(os.environ.get(name) for name in MODEL_KEYS)


def override_store_available() -> bool:
    """Whether the override store answers a ping."""
    try:
        import redis

        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        return bool(redis.from_url(url, socket_timeout=TIMEOUT_SECONDS).ping())
    except Exception:
        return False


def tracing_configured() -> bool:
    """Whether tracing has somewhere to send spans."""
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def versions_agree(base_url: str) -> bool | None:
    """Whether this client is the same build as the agent (E28-T11)."""
    from agent.version import same_as

    try:
        status, payload = _get(f"{base_url}/version")
    except Exception:
        return None
    if status != 200 or not isinstance(payload, dict):
        return None
    theirs = str(payload.get("version") or "")
    if not theirs:
        return None
    return same_as(theirs)
