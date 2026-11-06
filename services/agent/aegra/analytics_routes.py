"""Usage analytics for operators."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from agent.aegra.analytics_export import as_csv
from agent.aegra.eval_routes import _require_developer
from agent.src.analytics import queries
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/analytics", tags=["analytics"])


class SummaryOut(BaseModel):
    """Volume, reliability, latency, tokens and satisfaction."""

    window_days: int
    runs: int
    threads: int
    users: int
    successes: int
    errors: int
    conversations: int
    in_flight: int
    stale: int
    interrupted: int
    success_rate: float | None = None
    p50_seconds: float | None = None
    p95_seconds: float | None = None
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cache_hit_rate: float | None = None
    feedback_up: int
    feedback_down: int
    satisfaction: float | None = None


class ErrorBudgetOut(BaseModel):
    """How much of the allowed failure this window has spent."""

    window_days: int
    state: str
    used: float
    failures_left: int
    may_deploy: bool
    warn: bool
    exceptional: bool
    reason: str = ""


class TimeseriesPointOut(BaseModel):
    """One bucket of a time series: when, and how many."""

    bucket: str
    runs: int
    errors: int
    p95_seconds: float | None = None


class TimeseriesOut(BaseModel):
    """Runs, errors and p95 over time, with empty buckets filled."""

    bucket: str
    points: list[TimeseriesPointOut]


class ModelsOut(BaseModel):
    """Per-model volume, tokens, latency, errors and cost."""

    window_days: int
    models: list[dict[str, Any]]
    total_cost: str | float | None = None
    currency: str = ""
    rate_card_version: str = ""
    unpriced: list[Any] = []
    complete: bool = True


class AssistantsOut(BaseModel):
    """Volume, outcome and latency per assistant."""

    window_days: int
    assistants: list[dict[str, Any]]


class BreachOut(BaseModel):
    """A threshold that was crossed, and by how much."""

    name: str
    detail: str


class ThresholdsOut(BaseModel):
    """The thresholds analytics compares against, and any breaches."""

    error_rate: float | None = None
    p95_seconds: float | None = None
    spend: float | None = None


class AlertsOut(BaseModel):
    """Anything over a configured limit, and the limits applied."""

    ok: bool
    breaches: list[BreachOut]
    thresholds: ThresholdsOut


class ErrorsOut(BaseModel):
    """Failures by class — never by message."""

    window_days: int
    classes: list[dict[str, Any]]


def _window(days: int) -> queries.Window:
    return queries.Window(days=days)


def _unavailable(exc: Exception) -> HTTPException:
    """A dashboard that cannot reach the database should say so."""
    logger.warning("Analytics query failed: %s", exc)
    return HTTPException(status_code=503, detail="Analytics unavailable")


@router.get("/summary", responses={200: {"model": SummaryOut}})
async def analytics_summary(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Volume, reliability, latency, tokens and satisfaction."""
    try:
        result = await queries.summary(_window(days))
    except Exception as exc:
        raise _unavailable(exc) from None

    return {
        "window_days": result.window_days,
        "runs": result.runs,
        "threads": result.threads,
        "users": result.users,
        "successes": result.successes,
        "errors": result.errors,
        "conversations": result.conversations,
        "in_flight": result.in_flight,
        "stale": result.stale,
        "interrupted": result.interrupted,
        "success_rate": result.success_rate,
        "p50_seconds": result.p50_seconds,
        "p95_seconds": result.p95_seconds,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cached_tokens": result.cached_tokens,
        "cache_hit_rate": result.cache_hit_rate,
        "feedback_up": result.feedback_up,
        "feedback_down": result.feedback_down,
        "satisfaction": result.satisfaction,
    }


class CsvResponse(Response):
    """Declares the media type the export actually sends."""

    media_type = "text/csv"


class UserRowOut(BaseModel):
    """One person's row, when per-user disclosure is enabled (PRIV-3)."""

    user_id: str
    runs: int
    threads: int
    tokens: int
    errors: int


class UsersOut(BaseModel):
    """Per-user activity, where a deployment has turned it on."""

    window_days: int
    users: list[UserRowOut]


@router.get(
    "/export",
    response_class=CsvResponse,
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string"}}},
            "description": "The rows as CSV, as an attachment.",
        }
    },
)
async def analytics_export(
    what: str = Query("models"),
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    _token: str = Depends(_require_developer),
) -> Response:
    """One report as a file, for the questions a dashboard cannot answer."""
    if what not in queries.EXPORTABLE:
        raise HTTPException(
            status_code=404,
            detail=f"No such report: {what}. Try one of {sorted(queries.EXPORTABLE)}.",
        )

    try:
        rows = await queries.export_rows(what, _window(days))
    except Exception as exc:
        raise _unavailable(exc) from None

    return Response(
        content=as_csv(rows),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{what}-{days}d.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/error-budget", responses={200: {"model": ErrorBudgetOut}})
async def analytics_error_budget(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    objective: float = Query(0.99, gt=0.0, lt=1.0),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """How much of the allowed failure this window has already spent."""
    from agent.aegra.analytics_error_budget import budget_from_counts

    try:
        result = await queries.summary(_window(days))
    except Exception as exc:
        raise _unavailable(exc) from None

    return {
        "window_days": result.window_days,
        **budget_from_counts(
            runs=result.runs, errors=result.errors, objective=objective
        ),
    }


@router.get("/timeseries", responses={200: {"model": TimeseriesOut}})
async def analytics_timeseries(
    days: int = Query(30, ge=1, le=queries.MAX_WINDOW_DAYS),
    bucket: str = Query("day", pattern="^(hour|day)$"),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Runs, errors and p95 over time, with empty buckets filled."""
    try:
        points = await queries.timeseries(_window(days), bucket=bucket)
    except Exception as exc:
        raise _unavailable(exc) from None
    return {"bucket": bucket, "points": points}


@router.get("/models", responses={200: {"model": ModelsOut}})
async def analytics_models(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Per-model volume, tokens, latency, errors and cost."""
    try:
        rows = await queries.by_model(_window(days))
    except Exception as exc:
        raise _unavailable(exc) from None

    from agent.aegra.rates_routes import price_tokens
    from agent.src.analytics.priced import priced_usage

    priced = priced_usage(rows, price=price_tokens)
    return {
        "window_days": _window(days).days,
        "models": priced["rows"],
        "total_cost": priced["total"],
        "currency": priced["currency"],
        "rate_card_version": priced["rate_card_version"],
        "unpriced": priced["unpriced"],
        "complete": priced["complete"],
    }


@router.get("/assistants", responses={200: {"model": AssistantsOut}})
async def analytics_assistants(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Volume, outcome and latency per assistant."""
    try:
        rows = await queries.by_assistant(_window(days))
    except Exception as exc:
        raise _unavailable(exc) from None
    return {"window_days": days, "assistants": rows}


async def _summary_for_alerts(days: int) -> dict[str, Any]:
    """The figures the thresholds are checked against."""
    from agent.aegra.rates_routes import price_tokens
    from agent.src.analytics.priced import priced_usage

    result = await queries.summary(_window(days))
    priced = priced_usage(await queries.by_model(_window(days)), price=price_tokens)
    return {
        "runs": result.runs,
        "errors": result.errors,
        "p95_seconds": result.p95_seconds,
        "total_cost": priced["total"],
        "complete": priced["complete"],
    }


def _alert_thresholds() -> Any:
    """The limits from the observability file, or none."""
    import yaml

    from agent.src.agent.config.loader import agent_config
    from agent.src.analytics.thresholds import from_config

    try:
        path = agent_config._resolve("observability", "runtime/observability.yaml")
        if not path.is_file():
            return from_config({})
        return from_config(yaml.safe_load(path.read_text()) or {})
    except Exception:
        logger.warning("Could not read alert thresholds", exc_info=True)
        return from_config({})


@router.get("/alerts", responses={200: {"model": AlertsOut}})
async def analytics_alerts(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Anything over a configured limit, and the limits applied."""
    from agent.src.analytics.thresholds import breaches

    limits = _alert_thresholds()
    try:
        window = await _summary_for_alerts(days)
    except Exception as exc:
        raise _unavailable(exc) from None

    found = breaches(window, limits)
    return {
        "ok": not found,
        "breaches": [{"name": b.name, "detail": b.detail} for b in found],
        "thresholds": {
            "error_rate": limits.error_rate,
            "p95_seconds": limits.p95_seconds,
            "spend": limits.spend,
        },
    }


@router.get("/errors", responses={200: {"model": ErrorsOut}})
async def analytics_errors(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Failures by class."""
    try:
        rows = await queries.errors(_window(days))
    except Exception as exc:
        raise _unavailable(exc) from None
    return {"window_days": _window(days).days, "classes": rows}


@router.get("/users", responses={200: {"model": UsersOut}})
async def analytics_users(
    days: int = Query(7, ge=1, le=queries.MAX_WINDOW_DAYS),
    limit: int = Query(50, ge=1, le=500),
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Per-user usage, when a deployment has enabled it."""
    enabled = _expose_users()
    try:
        breakdown = await queries.by_user(_window(days), enabled=enabled, limit=limit)
    except Exception as exc:
        raise _unavailable(exc) from None

    if not breakdown.enabled:
        raise HTTPException(status_code=404, detail=breakdown.reason)

    return {
        "window_days": _window(days).days,
        "users": [
            {
                "user_id": row.user_id,
                "runs": row.runs,
                "threads": row.threads,
                "tokens": row.tokens,
                "errors": row.errors,
            }
            for row in breakdown.rows
        ],
    }


def _expose_users() -> bool:
    """`analytics.expose_users` in agent.yaml. Default false."""
    try:
        from agent.src.agent.config import agent_config

        raw = agent_config.get_analytics_config() or {}
        return bool(raw.get("expose_users", False))
    except Exception:
        return False
