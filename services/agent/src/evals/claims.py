"""Claiming an eval run, so two workers never do the same one.

Named `claims`, not `queue`: a module called `queue.py` shadows
the standard library for anything that puts its directory on
`sys.path`, and psycopg imports `queue` internally — which is
exactly how this was first discovered.

The queue is the `evals` table, which already carried the state
machine — `eval_status` of `in_progress`, `completed` or `error`,
indexed, with queries selecting by it. What it had no way to
express was *pending, and nobody has started it*, because the
work was pushed over HTTP to a service that began immediately.

Postgres rather than Temporal, deliberately. Durable execution
earns its complexity when an interrupted step cannot be repeated
— sending money is their example. An eval run is idempotent: a
dead worker costs the time, and the row goes back on the queue.
Requiring Temporal here would also tie evals to
`event_service_enabled`, which ships off.

Two workers, one row: `FOR UPDATE SKIP LOCKED` hands the row to
exactly one of them and lets the other walk past rather than
block. The lease is what covers the worker dying afterwards —
`claimed_until` in the past means the claim is void and the row
is available again, which is the same shape the cron table uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

PENDING = "pending"
RUNNING = "in_progress"
DONE = "completed"
FAILED = "error"

#: How long a worker may hold a row before another may take it.
#: Longer than the slowest eval, or a run still going is stolen
#: and done twice; short enough that a crash is not a long outage.
LEASE = timedelta(minutes=45)


@dataclass(frozen=True)
class Claim:
    """One worker's claim on an eval row."""

    eval_id: int
    config_hash: str
    force_reeval: bool


SCHEMA = """
ALTER TABLE evals ADD COLUMN IF NOT EXISTS claimed_until TIMESTAMPTZ;
ALTER TABLE evals ADD COLUMN IF NOT EXISTS claimed_by    TEXT;
CREATE INDEX IF NOT EXISTS evals_claimable
    ON evals (eval_status, claimed_until);
"""

#: The claim.
#:
#: A row is available when it is pending, or when it is running
#: under a lease that has expired — the second half is the only
#: thing that recovers a worker killed mid-run.
#:
#: SKIP LOCKED is what makes a second worker useful rather than a
#: queue of one: it steps over rows another transaction holds
#: instead of waiting behind them.
_CLAIM = """
UPDATE evals SET
    eval_status   = %(running)s,
    claimed_by    = %(worker)s,
    claimed_until = %(until)s,
    updated_at    = NOW()
WHERE id = (
    SELECT id FROM evals
    WHERE eval_status = %(pending)s
       OR (eval_status = %(running)s AND claimed_until < NOW())
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING id, config_hash, force_reeval
"""


def ensure_schema(connection: Any) -> None:
    """Add the lease columns. Safe to run on every worker start."""
    with connection.cursor() as cur:
        cur.execute(SCHEMA)
    connection.commit()


def claim(connection: Any, *, worker: str, lease: timedelta = LEASE) -> Claim | None:
    """Take one run, or return None when there is nothing to do."""
    until = datetime.now(timezone.utc) + lease
    with connection.cursor() as cur:
        cur.execute(
            _CLAIM,
            {
                "running": RUNNING,
                "pending": PENDING,
                "worker": worker,
                "until": until,
            },
        )
        row = cur.fetchone()
    connection.commit()
    if not row:
        return None
    return Claim(eval_id=row[0], config_hash=row[1], force_reeval=bool(row[2]))


def extend(connection: Any, eval_id: int, *, lease: timedelta = LEASE) -> None:
    """Push the lease out; a long eval must not be stolen mid-run."""
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE evals SET claimed_until = %s, updated_at = NOW() WHERE id = %s",
            (datetime.now(timezone.utc) + lease, eval_id),
        )
    connection.commit()


def release(connection: Any, eval_id: int, *, status: str, detail: str = "") -> None:
    """Finish a run, and drop the lease with it.

    The lease is cleared whatever the outcome. A failed run that
    kept its claim would sit unavailable until the lease expired,
    which reads as the queue being stuck.
    """
    if status not in (DONE, FAILED):
        raise ValueError(f"release expects {DONE} or {FAILED}, got {status!r}")
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE evals SET
                eval_status   = %s,
                claimed_until = NULL,
                claimed_by    = NULL,
                updated_at    = NOW(),
                completed_at  = NOW()
            WHERE id = %s
            """,
            (status, eval_id),
        )
    connection.commit()


def enqueue(connection: Any, *, config_hash: str, force: bool = False) -> int:
    """Ask for a run. Returns the row id; starts nothing itself.

    This is what `POST /evals/run` becomes. The agent writes a row
    and answers; it no longer makes a synchronous HTTP call to a
    service that may have scaled to zero.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evals (config_hash, eval_status, force_reeval)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (config_hash, PENDING, force),
        )
        (new_id,) = cur.fetchone()
    connection.commit()
    return int(new_id)
