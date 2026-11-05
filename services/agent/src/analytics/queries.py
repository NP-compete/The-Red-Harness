"""Usage analytics, derived from tables the platform already writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_WINDOW_DAYS = settings.ANALYTICS_MAX_WINDOW_DAYS

_TERMINAL = ["success", "error", "timeout"]

_RECOVERABLE = ["interrupted"]

_STALE_AFTER_SECONDS = settings.ANALYTICS_STALE_RUN_SECONDS

_CLIENT_ONLY = "(config->'metadata'->>'trace_id') IS NOT NULL"
_CLIENT_ONLY_R = "(r.config->'metadata'->>'trace_id') IS NOT NULL"

_TOKENS_CTE = """
derived AS (
    SELECT
        r.run_id,
        COALESCE(SUM((m -> 'usage_metadata' ->> 'input_tokens')::bigint), 0)  AS input_tokens,
        COALESCE(SUM((m -> 'usage_metadata' ->> 'output_tokens')::bigint), 0) AS output_tokens
    FROM runs r
    CROSS JOIN LATERAL jsonb_array_elements(
        CASE WHEN jsonb_typeof(r.output -> 'messages') = 'array'
             THEN r.output -> 'messages' ELSE '[]'::jsonb END
    ) AS m
    WHERE r.created_at >= now() - make_interval(days => %(days)s)
          AND (r.config->'metadata'->>'trace_id') IS NOT NULL
    GROUP BY r.run_id
),
tokens AS (
    SELECT
        r.run_id,
        COALESCE(
            (r.execution_params #>> '{usage,input_tokens}')::bigint,
            d.input_tokens, 0
        ) AS input_tokens,
        COALESCE(
            (r.execution_params #>> '{usage,output_tokens}')::bigint,
            d.output_tokens, 0
        ) AS output_tokens,
        -- Only the recorded path reports this. The derived fallback
        -- reads message usage_metadata, which has no cache field, so
        -- older runs report 0 rather than a wrong number.
        COALESCE((r.execution_params #>> '{usage,cached_tokens}')::bigint, 0)
            AS cached_tokens
    FROM runs r
    LEFT JOIN derived d ON d.run_id = r.run_id
    WHERE r.created_at >= now() - make_interval(days => %(days)s)
          AND (r.config->'metadata'->>'trace_id') IS NOT NULL
)
"""


@dataclass
class Window:
    """The period a figure covers, carried alongside it."""

    days: int

    def __post_init__(self) -> None:
        """Clamp the window so a hand-written query cannot scan the whole table."""
        self.days = max(1, min(int(self.days), MAX_WINDOW_DAYS))


@dataclass
class Summary:
    """Headline counters for one analytics window."""

    window_days: int
    runs: int = 0
    conversations: int = 0
    threads: int = 0
    users: int = 0
    successes: int = 0
    errors: int = 0
    in_flight: int = 0
    interrupted: int = 0
    stale: int = 0
    p50_seconds: float = 0.0
    p95_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    feedback_up: int = 0
    feedback_down: int = 0

    @property
    def success_rate(self) -> float | None:
        """Share of *finished* runs that worked, or None if none have."""
        finished = self.successes + self.errors
        return round(self.successes / finished * 100, 1) if finished else None

    @property
    def cache_hit_rate(self) -> float | None:
        """Share of input tokens served from the cached prefix."""
        if not self.input_tokens:
            return None
        return round(self.cached_tokens / self.input_tokens * 100, 1)

    @property
    def satisfaction(self) -> float | None:
        """Thumbs-up share of rated runs, or None when nothing was rated."""
        rated = self.feedback_up + self.feedback_down
        return round(self.feedback_up / rated * 100, 1) if rated else None


def _connect() -> Any:
    """Borrow a connection from the shared pool."""
    from agent.src.db.pool import connection

    return connection()


async def summary(window: Window) -> Summary:
    """Headline figures for the window."""
    sql = f"""
    WITH {_TOKENS_CTE},
    scoped AS (
        SELECT r.run_id, r.thread_id, r.user_id, r.status, r.updated_at,
               EXTRACT(EPOCH FROM (r.updated_at - r.created_at)) AS seconds
        FROM runs r
        WHERE r.created_at >= now() - make_interval(days => %(days)s)
          AND {_CLIENT_ONLY_R}
    )
    SELECT
        COUNT(*)                                             AS runs,
        -- Every query here is already client-only, so a thread in
        -- scope *is* a conversation. Both names are returned because
        -- the API had shipped with them; they are the same number by
        -- construction rather than by coincidence.
        COUNT(DISTINCT thread_id)                            AS conversations,
        COUNT(DISTINCT thread_id)                            AS threads,
        COUNT(DISTINCT user_id)                              AS users,
        COUNT(*) FILTER (WHERE status = 'success')           AS successes,
        COUNT(*) FILTER (WHERE status = 'error')             AS errors,
        COUNT(*) FILTER (WHERE NOT (status = ANY(%(terminal)s))
                           AND NOT (status = ANY(%(recoverable)s))
                           AND updated_at >= now() - make_interval(
                                 secs => %(stale_after)s))          AS in_flight,
        COUNT(*) FILTER (WHERE status = ANY(%(recoverable)s))        AS interrupted,
        -- Non-terminal and untouched for longer than any run may
        -- legitimately take. Reported rather than hidden: a growing
        -- number here means pods are dying mid-run.
        COUNT(*) FILTER (WHERE NOT (status = ANY(%(terminal)s))
                           AND NOT (status = ANY(%(recoverable)s))
                           AND updated_at < now() - make_interval(
                                 secs => %(stale_after)s))           AS stale,
        -- Percentiles over finished runs only. An in-flight run's
        -- elapsed time is not its duration, and including it drags
        -- p95 toward "however long ago the request arrived".
        COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY seconds) FILTER (WHERE status = ANY(%(terminal)s)), 0) AS p50,
        COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (
            ORDER BY seconds) FILTER (WHERE status = ANY(%(terminal)s)), 0) AS p95,
        COALESCE((SELECT SUM(input_tokens) FROM tokens), 0)  AS input_tokens,
        COALESCE((SELECT SUM(output_tokens) FROM tokens), 0) AS output_tokens,
        COALESCE((SELECT SUM(cached_tokens) FROM tokens), 0) AS cached_tokens
    FROM scoped
    """
    params = {
        "days": window.days,
        "terminal": _TERMINAL,
        "recoverable": _RECOVERABLE,
        "stale_after": _STALE_AFTER_SECONDS,
    }

    async with _connect() as conn:
        row = await (await conn.execute(sql, params)).fetchone() or {}
        feedback = (
            await (
                await conn.execute(
                    """
                SELECT
                    COUNT(*) FILTER (WHERE feedback = 'up')   AS up,
                    COUNT(*) FILTER (WHERE feedback = 'down') AS down
                FROM message_feedback
                WHERE created_at >= now() - make_interval(days => %(days)s)
                """,
                    {"days": window.days},
                )
            ).fetchone()
            or {}
        )

    return Summary(
        window_days=window.days,
        runs=int(row.get("runs") or 0),
        conversations=int(row.get("conversations") or 0),
        threads=int(row.get("threads") or 0),
        users=int(row.get("users") or 0),
        successes=int(row.get("successes") or 0),
        errors=int(row.get("errors") or 0),
        in_flight=int(row.get("in_flight") or 0),
        stale=int(row.get("stale") or 0),
        interrupted=int(row.get("interrupted") or 0),
        p50_seconds=round(float(row.get("p50") or 0), 2),
        p95_seconds=round(float(row.get("p95") or 0), 2),
        input_tokens=int(row.get("input_tokens") or 0),
        output_tokens=int(row.get("output_tokens") or 0),
        cached_tokens=int(row.get("cached_tokens") or 0),
        feedback_up=int(feedback.get("up") or 0),
        feedback_down=int(feedback.get("down") or 0),
    )


async def timeseries(window: Window, bucket: str = "day") -> list[dict[str, Any]]:
    """Runs, errors and p95 per bucket."""
    unit = "hour" if bucket == "hour" else "day"
    sql = f"""
    WITH bounds AS (
        SELECT date_trunc(%(unit)s, now() - make_interval(days => %(days)s))
               + ('1 ' || %(unit)s)::interval AS first_bucket
    ),
    buckets AS (
        SELECT generate_series(
            (SELECT first_bucket FROM bounds),
            date_trunc(%(unit)s, now()),
            ('1 ' || %(unit)s)::interval
        ) AS bucket
    ),
    scoped AS (
        SELECT date_trunc(%(unit)s, created_at) AS bucket,
               status,
               EXTRACT(EPOCH FROM (updated_at - created_at)) AS seconds
        FROM runs
        WHERE created_at >= (SELECT first_bucket FROM bounds)
          AND {_CLIENT_ONLY}
    )
    SELECT
        b.bucket,
        COUNT(s.*)                                   AS runs,
        COUNT(s.*) FILTER (WHERE s.status = 'error') AS errors,
        COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (
            ORDER BY s.seconds) FILTER (WHERE s.status = ANY(%(terminal)s)), 0) AS p95
    FROM buckets b
    LEFT JOIN scoped s ON s.bucket = b.bucket
    GROUP BY b.bucket
    ORDER BY b.bucket
    """
    async with _connect() as conn:
        rows = await (
            await conn.execute(
                sql,
                {"unit": unit, "days": window.days, "terminal": _TERMINAL},
            )
        ).fetchall()

    return [
        {
            "bucket": row["bucket"].isoformat(),
            "runs": int(row["runs"] or 0),
            "errors": int(row["errors"] or 0),
            "p95_seconds": round(float(row["p95"] or 0), 2),
        }
        for row in rows
    ]


async def by_model(window: Window) -> list[dict[str, Any]]:
    """Volume, tokens, latency and error rate per model."""
    sql = """
    WITH per_run AS (
        SELECT
            r.run_id,
            r.status,
            EXTRACT(EPOCH FROM (r.updated_at - r.created_at)) AS seconds,
            COALESCE(r.execution_params #> '{usage,models}', '{}'::jsonb) AS models
        FROM runs r
        WHERE r.created_at >= now() - make_interval(days => %(days)s)
          AND (r.config->'metadata'->>'trace_id') IS NOT NULL
    ),
    -- Same fallback as the token totals: runs that predate per-model
    -- recording are read from their output messages where they have
    -- any. Only `ai` messages count as calls — a human turn has no
    -- model and would inflate the figure that stands in for cost.
    derived AS (
        SELECT
            p.run_id,
            COALESCE(msg -> 'response_metadata' ->> 'model_name', 'unknown') AS model,
            COALESCE(SUM((msg -> 'usage_metadata' ->> 'input_tokens')::bigint), 0)  AS input_tokens,
            COALESCE(SUM((msg -> 'usage_metadata' ->> 'output_tokens')::bigint), 0) AS output_tokens,
            COUNT(*)                                                                AS calls
        FROM per_run p
        JOIN runs r ON r.run_id = p.run_id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.output -> 'messages') = 'array'
                 THEN r.output -> 'messages' ELSE '[]'::jsonb END
        ) AS msg
        WHERE p.models = '{}'::jsonb
          AND msg ->> 'type' = 'ai'
        GROUP BY 1, 2
    ),
    -- Runs with neither source still have to appear somewhere. They
    -- land under 'unrecorded' rather than being silently dropped or
    -- folded into a real model's totals — a row of zeroes against a
    -- named model is a claim about that model that nothing supports.
    expanded AS (
        SELECT p.run_id, p.status, p.seconds,
               m.key AS model,
               COALESCE((m.value ->> 'input_tokens')::bigint, 0)  AS input_tokens,
               COALESCE((m.value ->> 'output_tokens')::bigint, 0) AS output_tokens,
               COALESCE((m.value ->> 'calls')::bigint, 0)         AS calls
        FROM per_run p
        CROSS JOIN LATERAL jsonb_each(p.models) AS m
        UNION ALL
        SELECT p.run_id, p.status, p.seconds,
               d.model, d.input_tokens, d.output_tokens, d.calls
        FROM per_run p
        JOIN derived d ON d.run_id = p.run_id
        UNION ALL
        SELECT p.run_id, p.status, p.seconds, 'unrecorded', 0, 0, 0
        FROM per_run p
        WHERE p.models = '{}'::jsonb
          AND NOT EXISTS (SELECT 1 FROM derived d WHERE d.run_id = p.run_id)
    )
    SELECT
        model,
        COUNT(DISTINCT run_id)                                  AS runs,
        SUM(calls)                                              AS calls,
        COUNT(DISTINCT run_id) FILTER (WHERE status = 'error')  AS errors,
        COALESCE(SUM(input_tokens), 0)                          AS input_tokens,
        COALESCE(SUM(output_tokens), 0)                         AS output_tokens,
        COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (
            ORDER BY seconds
        ) FILTER (WHERE status = ANY(%(terminal)s)), 0)         AS p95
    FROM expanded
    GROUP BY 1
    ORDER BY runs DESC
    """
    async with _connect() as conn:
        rows = await (
            await conn.execute(sql, {"days": window.days, "terminal": _TERMINAL})
        ).fetchall()

    return [
        {
            "model": row["model"],
            "runs": int(row["runs"]),
            "calls": int(row["calls"] or 0),
            "errors": int(row["errors"]),
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "p95_seconds": round(float(row["p95"] or 0), 2),
        }
        for row in rows
    ]


_ERROR_CLASSES: list[tuple[str, tuple[str, ...]]] = [
    ("model_timeout", ("timeout", "timed out", "deadline exceeded")),
    ("model_rate_limit", ("rate limit", "429", "resource exhausted", "quota")),
    ("model_refused", ("safety", "blocked", "recitation", "finish_reason")),
    (
        "model_config",
        (
            "credentials",
            "api key",
            "api_key",
            "failed to create",
            "model not found",
            "unknown model",
            "invalid_grant",
            "unauthorized",
            "permission denied",
            "403",
        ),
    ),
    ("context_too_long", ("context length", "token limit", "too many tokens")),
    ("retries_exhausted", ("max retries", "retries exceeded")),
    ("storage", ("psycopg", "postgres", "connection refused", "redis")),
    ("cancelled", ("cancelled", "canceled", "interrupted")),
    (
        "agent_defect",
        (
            "indices must be",
            "attributeerror",
            "typeerror",
            "keyerror",
            "nonetype",
            "not subscriptable",
            "unexpected keyword",
        ),
    ),
    ("tool_failure", ("tool", "mcp", "subprocess")),
]


def classify_error(message: str | None) -> str:
    """Bucket an exception string. Never returns the string itself."""
    if not message:
        return "unknown"
    lowered = message.lower()
    for label, needles in _ERROR_CLASSES:
        if any(needle in lowered for needle in needles):
            return label
    return "other"


async def errors(window: Window) -> list[dict[str, Any]]:
    """Failure counts by class, most frequent first."""
    async with _connect() as conn:
        rows = await (
            await conn.execute(
                f"""
                SELECT error_message, updated_at
                FROM runs
                WHERE status = 'error'
                  AND created_at >= now() - make_interval(days => %(days)s)
                  AND {_CLIENT_ONLY}
                ORDER BY updated_at DESC
                LIMIT 5000
                """,
                {"days": window.days},
            )
        ).fetchall()

    counts: dict[str, dict[str, Any]] = {}
    for row in rows:
        label = classify_error(row.get("error_message"))
        entry = counts.setdefault(
            label, {"class": label, "count": 0, "last_seen": None}
        )
        entry["count"] += 1
        seen = row.get("updated_at")
        if seen and (entry["last_seen"] is None or seen > entry["last_seen"]):
            entry["last_seen"] = seen

    return sorted(
        (
            {
                **entry,
                "last_seen": entry["last_seen"].isoformat()
                if entry["last_seen"]
                else None,
            }
            for entry in counts.values()
        ),
        key=lambda e: -e["count"],
    )


@dataclass
class UserRow:
    """One user's activity over the window."""

    user_id: str
    runs: int = 0
    threads: int = 0
    tokens: int = 0
    errors: int = 0


@dataclass
class UserBreakdown:
    """Per-user usage. Off unless a deployment turns it on."""

    enabled: bool
    rows: list[UserRow] = field(default_factory=list)
    reason: str = ""


async def by_user(window: Window, *, enabled: bool, limit: int = 50) -> UserBreakdown:
    """Usage attributed to named people."""
    if not enabled:
        return UserBreakdown(
            enabled=False,
            reason="per-user analytics are disabled (analytics.expose_users)",
        )

    sql = f"""
    WITH {_TOKENS_CTE}
    SELECT
        r.user_id,
        COUNT(*)                                   AS runs,
        COUNT(DISTINCT r.thread_id)                AS threads,
        COUNT(*) FILTER (WHERE r.status = 'error') AS errors,
        COALESCE(SUM(t.input_tokens + t.output_tokens), 0) AS tokens
    FROM runs r
    LEFT JOIN tokens t ON t.run_id = r.run_id
    WHERE r.created_at >= now() - make_interval(days => %(days)s)
          AND (r.config->'metadata'->>'trace_id') IS NOT NULL
    GROUP BY r.user_id
    ORDER BY runs DESC
    LIMIT %(limit)s
    """
    async with _connect() as conn:
        rows = await (
            await conn.execute(sql, {"days": window.days, "limit": limit})
        ).fetchall()

    return UserBreakdown(
        enabled=True,
        rows=[
            UserRow(
                user_id=row["user_id"],
                runs=int(row["runs"]),
                threads=int(row["threads"]),
                tokens=int(row["tokens"]),
                errors=int(row["errors"]),
            )
            for row in rows
        ],
    )


async def by_assistant(window: Window) -> list[dict[str, Any]]:
    """Volume, outcome and latency per assistant."""
    sql = f"""
    SELECT
        COALESCE(NULLIF(r.assistant_id::text, ''), 'unattributed') AS assistant,
        COUNT(*)                                                    AS runs,
        COUNT(*) FILTER (WHERE r.status = 'error')                  AS errors,
        COUNT(DISTINCT r.thread_id)                                 AS threads,
        PERCENTILE_CONT(0.95) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (r.updated_at - r.created_at))
        )                                                           AS p95
    FROM runs r
    WHERE r.created_at >= now() - make_interval(days => %(days)s)
      -- Client traffic only. Without this the breakdown counts
      -- health checks and internal runs as spend, which is wrong
      -- in the direction that matters: it inflates the bill
      -- attributed to whichever assistant the machinery uses.
      AND {_CLIENT_ONLY_R}
    GROUP BY 1
    ORDER BY runs DESC
    """

    async with _connect() as conn:
        rows = await (await conn.execute(sql, {"days": window.days})).fetchall()

    return [
        {
            "assistant": row["assistant"],
            "runs": int(row["runs"] or 0),
            "errors": int(row["errors"] or 0),
            "threads": int(row["threads"] or 0),
            "p95_seconds": (
                round(float(row["p95"]), 2) if row["p95"] is not None else None
            ),
        }
        for row in rows
    ]


EXPORTABLE: dict[str, str] = {
    "models": "by_model",
    "errors": "errors",
    "timeseries": "timeseries",
    "assistants": "by_assistant",
}


async def export_rows(what: str, window: Window) -> list[dict[str, Any]]:
    """The rows behind one report, for writing to a file."""
    name = EXPORTABLE.get(what)
    if name is None:
        raise KeyError(what)
    rows: list[dict[str, Any]] = await globals()[name](window)
    return rows
