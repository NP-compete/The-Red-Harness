"""Lifecycle state persistence — Postgres-based recovery."""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

POD_ID: str = os.environ.get(
    "POD_NAME",
    os.environ.get("HOSTNAME", f"local-{os.getpid()}"),
)


class RunExecutionContext(BaseModel):
    """Snapshot of everything needed to resume an interrupted run."""

    model_name: str = Field(description="LLM model identifier")
    config_hash: str = Field(description="Hash of the graph config at build time")
    assistant_id: Optional[str] = Field(default=None, description="Aegra assistant ID")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID")
    encrypted_refresh_token: Optional[str] = Field(
        default=None, description="Fernet-encrypted refresh token"
    )
    mcp_server_names: list[str] = Field(
        default_factory=list, description="MCP servers active at time of run"
    )
    orchestrator_config_snapshot: dict[str, Any] = Field(
        default_factory=dict, description="Orchestrator config at time of run"
    )


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from an arbitrary secret string."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _sign_on_secret() -> str:
    """The single sign-on client secret, wherever it is configured."""
    live = os.environ.get("SSO_CLIENT_SECRET", "").strip()
    if live:
        return live
    try:
        from agent.src.settings import settings

        if settings.SSO_CLIENT_SECRET:
            return str(settings.SSO_CLIENT_SECRET)
    except Exception:
        pass
    return ""


def sealing_secret() -> str:
    """The secret the key that seals stored tokens is derived from."""
    dedicated = os.environ.get("TOKEN_SEALING_SECRET", "").strip()
    return dedicated or _sign_on_secret()


def sealing_secrets() -> list[str]:
    """Every secret that may open a stored token, current first."""
    offered = [
        sealing_secret(),
        os.environ.get("TOKEN_SEALING_SECRET_PREVIOUS", "").strip(),
        _sign_on_secret(),
    ]
    kept: list[str] = []
    for one in offered:
        if one and one not in kept:
            kept.append(one)
    return kept


def open_sealed_token(sealed: str) -> str:
    """A stored token, opened by whichever generation sealed it."""
    from agent.src.security.key_generations import open_with

    return open_with(
        sealing_secrets(), sealed, lambda key, value: decrypt_token(value, key)
    )


def _get_encryption_secret() -> str:
    """The secret stored tokens are sealed with."""
    return sealing_secret()


def encrypt_token(token: str, secret: str) -> str:
    """Encrypt a token string using Fernet with the derived key."""
    from cryptography.fernet import Fernet

    key = _derive_fernet_key(secret)
    f = Fernet(key)
    return str(f.encrypt(token.encode("utf-8")).decode("utf-8"))


def decrypt_token(encrypted: str, secret: str) -> str:
    """Decrypt a Fernet-encrypted token string."""
    from cryptography.fernet import Fernet

    key = _derive_fernet_key(secret)
    f = Fernet(key)
    return str(f.decrypt(encrypted.encode("utf-8")).decode("utf-8"))


def _get_active_runs() -> dict[str, Any]:
    """Get active runs from the Aegra API core module."""
    try:
        from aegra_api.core.active_runs import active_runs

        return dict(active_runs)
    except ImportError:
        logger.debug("aegra_api.core.active_runs not available")
        return {}
    except Exception as exc:
        logger.debug("Failed to get active runs: %s", exc)
        return {}


def _update_run_status_postgres(
    run_id: str,
    status: str,
    claimed_by: Optional[str] = None,
) -> bool:
    """Update the run status in PostgreSQL using sync psycopg."""
    try:
        import psycopg

        from agent.src.settings import settings

        with psycopg.connect(settings.database_uri) as conn:
            with conn.cursor() as cur:
                if claimed_by is not None:
                    cur.execute(
                        "UPDATE runs SET status = %s, claimed_by = %s, "
                        "updated_at = NOW() "
                        "WHERE run_id = %s AND status = 'running'",
                        (status, claimed_by, run_id),
                    )
                else:
                    cur.execute(
                        "UPDATE runs SET status = %s, updated_at = NOW() "
                        "WHERE run_id = %s AND status = 'running'",
                        (status, run_id),
                    )
                updated = bool(cur.rowcount > 0)
            conn.commit()

        if updated:
            logger.info("Updated run %s status to '%s' in Postgres", run_id, status)
        return updated
    except Exception as exc:
        logger.warning("Failed to update run %s status in Postgres: %s", run_id, exc)
        return False


def persist_inflight_runs() -> int:
    """Expire leases on active runs so Aegra's LeaseReaper recovers them."""
    active = _get_active_runs()
    if active:
        run_ids = list(active.keys())
        logger.info(
            "Read %d active run(s) from in-memory active_runs dict", len(run_ids)
        )
    else:
        run_ids = []

    if not run_ids:
        logger.info("No inflight runs to persist")
        return 0

    persisted = _expire_run_leases_batch(run_ids)

    logger.info(
        "Expired leases on %d/%d inflight runs — LeaseReaper will re-enqueue them",
        persisted,
        len(run_ids),
    )
    return persisted


def _expire_run_leases_batch(run_ids: list[str]) -> int:
    """Set lease_expires_at to the past for all given runs in a single query."""
    if not run_ids:
        return 0
    try:
        import psycopg

        from agent.src.settings import settings

        with psycopg.connect(settings.database_uri) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE runs SET lease_expires_at = NOW() - INTERVAL '1 second', "
                    "execution_params = COALESCE(execution_params, '{}'::jsonb) || "
                    "jsonb_build_object('started_by_pod', %s::text, "
                    "'killed_at', NOW()::text), "
                    "updated_at = NOW() "
                    "WHERE run_id = ANY(%s) AND status = 'running'",
                    (POD_ID, run_ids),
                )
                updated = cur.rowcount or 0
            conn.commit()

        if updated:
            logger.info(
                "Expired leases for %d run(s) (started_by=%s) — reaper will recover",
                updated,
                POD_ID,
            )
        return updated
    except Exception as exc:
        logger.warning("Failed to expire leases for runs %s: %s", run_ids, exc)
        return 0


async def resume_interrupted_runs(
    db_uri: str,
    resume_fn: Callable,
) -> dict[str, str]:
    """Resume runs marked as interrupted in Postgres."""
    try:
        from agent.src.settings import settings as app_settings

        max_batch = app_settings.LIFECYCLE_MAX_RESUME_BATCH
        lease_seconds = app_settings.LIFECYCLE_LEASE_SECONDS
    except Exception:
        max_batch = 10
        lease_seconds = 300

    results: dict[str, str] = {}

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT run_id, thread_id, assistant_id, execution_params::text "
                    "FROM runs "
                    "WHERE status IN ('running', 'interrupted') "
                    "AND (lease_expires_at IS NULL "
                    "     OR lease_expires_at < NOW()) "
                    "ORDER BY updated_at ASC "
                    "LIMIT %s "
                    "FOR UPDATE SKIP LOCKED",
                    (max_batch,),
                )
                rows = await cur.fetchall()

                for row in rows:
                    run_id, thread_id = row[0], row[1]

                    await cur.execute(
                        "UPDATE runs SET claimed_by = %s, "
                        "lease_expires_at = NOW() + %s * INTERVAL '1 second', "
                        "status = 'running', "
                        "updated_at = NOW() "
                        "WHERE run_id = %s",
                        (POD_ID, lease_seconds, run_id),
                    )

                    try:
                        await resume_fn(run_id, thread_id)
                        await cur.execute(
                            "UPDATE runs SET status = 'success', "
                            "updated_at = NOW() WHERE run_id = %s",
                            (run_id,),
                        )
                        results[run_id] = "resumed"
                        logger.info("Resumed interrupted run %s", run_id)
                    except Exception as exc:
                        await cur.execute(
                            "UPDATE runs SET status = 'error', "
                            "updated_at = NOW() WHERE run_id = %s",
                            (run_id,),
                        )
                        results[run_id] = f"error: {exc}"
                        logger.warning("Failed to resume run %s: %s", run_id, exc)

            await conn.commit()

    except Exception as exc:
        logger.warning("Failed to query interrupted runs: %s", exc)

    return results


def build_execution_context(
    model_name: str,
    config_hash: str,
    assistant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    refresh_token: Optional[str] = None,
    mcp_server_names: Optional[list[str]] = None,
    orchestrator_config: Optional[dict[str, Any]] = None,
    encryption_secret: Optional[str] = None,
) -> dict:
    """Build a serializable execution context for inflight persistence."""
    encrypted = None
    if refresh_token:
        secret = encryption_secret or _get_encryption_secret()
        if secret:
            try:
                encrypted = encrypt_token(refresh_token, secret)
            except Exception as exc:
                logger.warning("Failed to encrypt refresh token: %s", exc)
        else:
            logger.warning(
                "Refresh token encryption skipped — SSO_CLIENT_SECRET not configured"
            )

    ctx = RunExecutionContext(
        model_name=model_name,
        config_hash=config_hash,
        assistant_id=assistant_id,
        user_id=user_id,
        encrypted_refresh_token=encrypted,
        mcp_server_names=mcp_server_names or [],
        orchestrator_config_snapshot=orchestrator_config or {},
    )
    return dict(ctx.model_dump())
