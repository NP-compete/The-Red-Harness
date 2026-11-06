"""Health check endpoint for OpenShift probes."""

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

from agent.aegra import __version__
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_start_time = time.monotonic()


async def check_database() -> dict[str, Any]:
    """Ping the Postgres database and measure latency."""
    try:
        from agent.src.settings import settings

        if not settings.database_uri:
            return {"status": "skipped", "reason": "no database_uri configured"}

        import psycopg

        t0 = time.monotonic()
        async with await psycopg.AsyncConnection.connect(settings.database_uri) as conn:
            await conn.execute("SELECT 1")
        latency_ms = (time.monotonic() - t0) * 1000

        return {"status": "ok", "latency_ms": round(latency_ms, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


async def check_redis() -> dict[str, Any]:
    """Ping the Redis server."""
    try:
        from agent.aegra.redis import get_redis_client

        client = get_redis_client()
        if client is None:
            return {"status": "skipped", "reason": "redis not configured"}

        t0 = time.monotonic()
        pong = await asyncio.to_thread(client.ping)
        latency_ms = (time.monotonic() - t0) * 1000

        return {
            "status": "ok" if pong else "error",
            "latency_ms": round(latency_ms, 1),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


def check_config() -> dict[str, Any]:
    """Validate that core configuration is present."""
    try:
        from agent.src.settings import settings

        issues: list[str] = []
        if not settings.database_uri:
            issues.append("database_uri not set")
        if settings.AGENT_PORT < 1 or settings.AGENT_PORT > 65535:
            issues.append(f"invalid port: {settings.AGENT_PORT}")

        if issues:
            return {"status": "warning", "issues": issues}
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


def check_cache() -> dict[str, Any]:
    """Return cache statistics if caching is enabled."""
    try:
        from agent.src.cache.metrics import get_stats

        stats = get_stats()
        return {"status": "ok", **stats}
    except Exception:
        return {"status": "skipped"}


def check_otel() -> dict[str, Any]:
    """Return OpenTelemetry initialization status."""
    try:
        from agent.aegra.otel import (
            _initialized,
            _otel_enabled,
            _resolve_config,
            is_tracing_enabled,
        )

        if not _initialized:
            return {"status": "not_initialized"}

        _, endpoint, _, _, _ = _resolve_config()

        sdk_version = None
        try:
            import opentelemetry

            sdk_version = getattr(opentelemetry, "__version__", "")
        except Exception:
            pass

        return {
            "status": "ok",
            "initialized": _initialized,
            "enabled": _otel_enabled,
            "tracing_active": is_tracing_enabled(),
            "endpoint": endpoint if _otel_enabled else None,
            "sdk_version": sdk_version,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


async def check_opa() -> dict[str, Any]:
    """Check OPA connectivity via its /health endpoint."""
    try:
        from agent.src.opa.config import (
            get_opa_timeout,
            get_opa_url,
            is_opa_enabled,
        )

        if not is_opa_enabled():
            return {"status": "disabled"}

        url = get_opa_url()
        timeout = get_opa_timeout()
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port_suffix = f":{parsed.port}" if parsed.port else ""
        base_url = f"{parsed.scheme}://{host}{port_suffix}"
        health_url = f"{base_url}/health"

        import httpx

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url)
            response.raise_for_status()
        latency_ms = (time.monotonic() - t0) * 1000

        return {"status": "ok", "latency_ms": round(latency_ms, 1), "url": base_url}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


_CRITICAL_CHECKS = frozenset({"database", "opa"})


async def get_health_status() -> dict[str, Any]:
    """Run all health checks and return a combined status."""
    from agent.aegra.mcp_health import check_llm_provider, check_mcp_servers

    checks: dict[str, Any] = {}

    checks["config"] = check_config()
    db_result, redis_result, mcp_result, llm_result, opa_result = await asyncio.gather(
        check_database(),
        check_redis(),
        check_mcp_servers(),
        check_llm_provider(),
        check_opa(),
    )
    checks["database"] = db_result
    checks["redis"] = redis_result
    checks["mcp_servers"] = mcp_result
    checks["llm_provider"] = llm_result
    checks["opa"] = opa_result
    checks["cache"] = check_cache()
    checks["otel"] = check_otel()

    critical_statuses = [
        checks[k].get("status", "unknown") for k in _CRITICAL_CHECKS if k in checks
    ]
    all_statuses = [c.get("status", "unknown") for c in checks.values()]

    if any(s == "error" for s in critical_statuses):
        overall = "unhealthy"
    elif any(s in ("error", "warning") for s in all_statuses):
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "version": __version__,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "checks": checks,
    }


def liveness_response() -> tuple[int, dict[str, Any]]:
    """Return (status_code, body) for liveness probes."""
    from agent.aegra.shutdown import is_shutting_down

    if is_shutting_down():
        return 503, {
            "status": "shutting_down",
            "version": __version__,
            "uptime_seconds": round(time.monotonic() - _start_time, 1),
        }

    return 200, {
        "status": "alive",
        "version": __version__,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
    }


async def health_response(path: str = "/health") -> tuple[int, dict[str, Any]]:
    """Return (status_code, body) for health and readiness endpoints."""
    if path in LIVENESS_PATHS:
        return liveness_response()

    from agent.aegra.shutdown import is_shutting_down

    if is_shutting_down():
        return 503, {
            "status": "shutting_down",
            "version": __version__,
            "uptime_seconds": round(time.monotonic() - _start_time, 1),
        }

    result = await get_health_status()
    code = 200 if result["status"] in ("healthy", "degraded") else 503
    return code, result


LIVENESS_PATHS = frozenset({"/livez"})
HEALTH_PATHS = frozenset({"/health", "/healthz", "/readyz", "/livez"})
