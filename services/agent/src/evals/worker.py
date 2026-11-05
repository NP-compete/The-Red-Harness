"""The eval worker: claim a queued run, do it, record it.

`harness eval-worker`. Replaces the eval-runner service, which
was a FastAPI pod the agent POSTed to. That shape had a defect
worth naming: the pod was KEDA-scaled to a minimum of zero, so
the agent made a synchronous call to something that could be
scaled away mid-request, and a run lost that way left nothing
behind.

Postgres is the queue — see `claims.py` for why that rather than
Temporal. The short version: an eval is idempotent, so the
guarantee durable execution sells is one evals do not need, and
requiring it would tie them to `event_service_enabled`.

The loop is deliberately boring. Claim one row, run it, keep the
lease warm while it runs, release it. Nothing here retries: a
failed run is recorded as failed and a person decides whether to
queue another, because an eval that silently re-runs is an eval
whose result nobody can reason about.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any

from agent.src.evals import claims
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

HERE = Path(__file__).resolve().parent

#: How long to wait when the queue is empty. Long enough not to
#: hammer Postgres, short enough that a queued eval starts while
#: somebody is still looking at the page that queued it.
IDLE_SECONDS = float(os.environ.get("EVAL_WORKER_IDLE_SECONDS", "5"))

#: The lease is renewed on this cadence, well inside its own
#: expiry, so a long run is never stolen from the worker doing it.
HEARTBEAT_SECONDS = float(os.environ.get("EVAL_WORKER_HEARTBEAT_SECONDS", "60"))


def agent_url() -> str:
    """Where the worker reaches the agent."""
    return os.environ.get("AGENT_BASE_URL", "http://agent:5002")


def _connect() -> Any:
    """Open a connection to the eval database."""
    import psycopg

    dsn = os.environ.get("EVAL_DATABASE_URL") or (
        f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'template_agent')} "
        f"user={os.environ.get('POSTGRES_USER', 'postgres')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'postgres')}"
    )
    return psycopg.connect(dsn)


def _heartbeat(connection: Any, eval_id: int, stop: threading.Event) -> None:
    """Hold the lease for as long as the run is actually running."""
    while not stop.wait(HEARTBEAT_SECONDS):
        try:
            claims.extend(connection, eval_id)
        except Exception as failed:  # noqa: BLE001
            # Losing the lease is bad but not worth killing the run
            # over: the reclaim is what covers it, and a second
            # worker starting the same eval is wasteful, not wrong.
            logger.warning("could not extend lease on eval %s: %s", eval_id, failed)
            return


def run_one(connection: Any, claim: claims.Claim) -> str:
    """Execute a claimed run. Returns the status to release it with.

    Delegates to `runs._run_eval`, which is the eval-runner
    service's orchestration minus its HTTP half. Spawning
    `lightspeed_runner` directly — which this did at first — runs
    the eval and discards it: the per-tag split, the re-score
    against `evaluation_results`, and the `write_eval_result` that
    makes a run visible to `/evals/results` all live there.
    """
    import asyncio

    from agent.src.evals import runs

    os.environ.setdefault("AGENT_HOST", agent_url())
    logger.info("eval %s (%s): starting", claim.eval_id, claim.config_hash)
    try:
        status = asyncio.run(
            runs._run_eval(
                pattern=None,
                config_hash=claim.config_hash,
                run_id=f"eval-{claim.eval_id}",
                eval_row_id=claim.eval_id,
            )
        )
    except Exception:
        logger.exception("eval %s: orchestration failed", claim.eval_id)
        return claims.FAILED

    # `_run_eval` handles its own failures and returns normally, so
    # "it did not raise" is not "it worked". Releasing on that alone
    # marked setup failures `completed` — a green row over a run
    # that never happened.
    if status == "error":
        logger.warning("eval %s: run reported error", claim.eval_id)
        return claims.FAILED
    logger.info("eval %s: completed (%s)", claim.eval_id, status)
    return claims.DONE


def run_worker(*, once: bool = False) -> int:
    """Poll the queue until stopped."""
    who = os.environ.get("HOSTNAME") or f"eval-worker-{os.getpid()}"
    stopping = threading.Event()

    def stop(signum: int, _frame: object) -> None:
        # Finish the run in hand, then exit. Killing it mid-eval
        # would leave a row held until its lease expired.
        """Finish the run in hand, then stop."""
        logger.info("signal %s: finishing the current run, then stopping", signum)
        stopping.set()

    for received in (signal.SIGTERM, signal.SIGINT):
        signal.signal(received, stop)

    connection = _connect()
    claims.ensure_schema(connection)
    # The service did this in its FastAPI lifespan; without it the
    # runner writes per-turn rows to a table that is not there.
    from agent.src.evals.store import ensure_table

    ensure_table()
    logger.info("eval worker %s: polling, agent at %s", who, agent_url())

    while not stopping.is_set():
        claim = claims.claim(connection, worker=who)
        if claim is None:
            if once:
                logger.info("nothing queued")
                return 0
            stopping.wait(IDLE_SECONDS)
            continue

        beat_stop = threading.Event()
        beat = threading.Thread(
            target=_heartbeat, args=(connection, claim.eval_id, beat_stop), daemon=True
        )
        beat.start()
        try:
            status = run_one(connection, claim)
        except Exception as broke:  # noqa: BLE001
            logger.exception("eval %s blew up", claim.eval_id)
            status = claims.FAILED
            del broke
        finally:
            beat_stop.set()
            beat.join(timeout=5)
            claims.release(connection, claim.eval_id, status=status)

        if once:
            return 0 if status == claims.DONE else 1

    logger.info("eval worker %s: stopped", who)
    return 0


def main() -> int:
    """Run the eval worker, once or until it is stopped."""
    return run_worker(once="--once" in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
