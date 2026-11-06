"""Upload files to a thread."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.attachments.config import AttachmentsConfig, ExtractionConfig
from agent.src.attachments.extract import (
    describe,
    extract_best,
    needs_base64,
    suffix_of,
)
from agent.src.attachments.safety import sanitise_filename, unique_name
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger


def suffix_or_file(name: str) -> str:
    """File extension, or `binary` when there is none to report."""
    return suffix_of(name) or "binary"


def _orchestrator_model() -> str:
    """Model used for transcription, from the agent's own config."""
    try:
        from agent.src.agent.config import agent_config

        configured = (agent_config.get_orchestrator_config() or {}).get("model")
        if isinstance(configured, dict):
            return str(configured.get("name") or settings.ATTACHMENT_MODEL)
        return str(configured or settings.ATTACHMENT_MODEL)
    except Exception:
        return settings.ATTACHMENT_MODEL


logger = get_python_logger()

router = APIRouter(tags=["attachments"])


def _config() -> AttachmentsConfig:
    """Attachment limits from agent.yaml, defaults when unset."""
    try:
        from agent.src.agent.config import agent_config

        return cast(AttachmentsConfig, agent_config.get_attachments_config())
    except Exception:
        logger.warning("Could not read attachments config — using defaults")
        return AttachmentsConfig()


def _extraction_config() -> ExtractionConfig:
    """Document-extraction engine from agent.yaml. Defaults to built-in."""
    try:
        from agent.src.agent.config import agent_config

        return cast(ExtractionConfig, agent_config.get_extraction_config())
    except Exception:
        logger.warning("Could not read extraction config — using built-in parsers")
        return ExtractionConfig()


_RUN_WAIT_SECONDS = settings.ATTACHMENT_RUN_WAIT_SECONDS
_RUN_POLL_SECONDS = settings.ATTACHMENT_RUN_POLL_SECONDS
_ACTIVE_RUN_STATUSES = {"pending", "running"}


async def _await_idle_thread(client: Any, thread_id: str) -> None:
    """Block until no run is executing on this thread."""
    import asyncio
    import time

    deadline = time.monotonic() + _RUN_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            runs = await client.get(f"/threads/{thread_id}/runs")
        except Exception:
            return
        if runs.status_code != 200:
            return
        body = runs.json()
        items = body if isinstance(body, list) else (body or {}).get("runs") or []
        if not any((r or {}).get("status") in _ACTIVE_RUN_STATUSES for r in items):
            return
        await asyncio.sleep(_RUN_POLL_SECONDS)

    logger.warning(
        "Thread %s still has an active run after %ss — writing anyway",
        thread_id,
        _RUN_WAIT_SECONDS,
    )


async def _read_bounded(upload: UploadFile, limit: int) -> bytes:
    """Read at most ``limit`` bytes, then one more to detect overflow."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"{upload.filename}: exceeds {limit} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _remember_for_retrieval(thread_id: str, name: str, path: str, text: str) -> None:
    """Make an attachment's text searchable, if this agent keeps documents."""
    try:
        from agent.src.agent.config import agent_config
        from agent.src.knowledge.attachments import remember_attachment
        from agent.src.knowledge.store import session_store

        remember_attachment(
            thread_id=thread_id,
            filename=name,
            path=path,
            text=text or "",
            store=session_store(),
            config=agent_config.get_knowledge_config(),
        )
    except Exception:
        logger.debug("Could not make %s searchable", name, exc_info=True)


class StoredAttachmentOut(BaseModel):
    """One stored file: where it went, how big, and whether its text came out."""

    filename: str
    path: str
    bytes: int
    text_extracted: bool
    truncated: bool
    engine: str = ""
    degraded: str | None = None


class AttachmentsStoredOut(BaseModel):
    """Everything one upload stored, with the summary the model is given."""

    attachments: list[StoredAttachmentOut]
    summary: str = ""


class ThreadAttachmentOut(BaseModel):
    """One file already attached to a conversation."""

    filename: str
    path: str
    chars: int


class ThreadAttachmentsOut(BaseModel):
    """Every file attached to a conversation."""

    attachments: list[ThreadAttachmentOut]


@router.post(
    "/threads/{thread_id}/attachments",
    responses={200: {"model": AttachmentsStoredOut}},
)
async def upload_attachments(
    thread_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    """Attach one or more files to a thread."""
    user_id = await authenticated_user_id(request, reject_anonymous=True)
    config = _config()
    extraction = _extraction_config()

    if not config.enabled:
        raise HTTPException(status_code=404, detail="Attachments are disabled")

    if len(files) > config.max_files_per_request:
        raise HTTPException(
            status_code=400,
            detail=f"At most {config.max_files_per_request} files per request",
        )

    import httpx

    from agent.src.settings import settings

    headers = {}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth

    async with httpx.AsyncClient(
        base_url=settings.loopback_base_url,
        headers=headers,
        timeout=60,
    ) as client:
        state = await client.get(f"/threads/{thread_id}/state")

        if state.status_code == 404:
            created = await client.post(
                "/threads",
                json={
                    "thread_id": thread_id,
                    "metadata": {"graph_id": "agent", "assistant_id": "agent"},
                    "if_exists": "do_nothing",
                },
            )
            if created.status_code not in (200, 201, 409):
                logger.error(
                    "Could not create thread %s for attachment: %s",
                    thread_id,
                    created.text[:200],
                )
                raise HTTPException(status_code=502, detail="Could not create thread")
            state = await client.get(f"/threads/{thread_id}/state")

        if state.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not read thread state")

        await _await_idle_thread(client, thread_id)
        refreshed = await client.get(f"/threads/{thread_id}/state")
        if refreshed.status_code == 200:
            state = refreshed

        payload = state.json() or {}
        values = payload.get("values") or {}
        assistant_id = ((payload.get("metadata") or {}).get("assistant_id")) or "agent"
        existing: dict[str, Any] = dict(values.get("files") or {})
        added: dict[str, Any] = {}

        def _size(entry: Any) -> int:
            if isinstance(entry, dict):
                return len(str(entry.get("content", "")))
            return len(str(entry))

        used = sum(_size(v) for v in existing.values())
        taken = {k.rsplit("/", 1)[-1] for k in existing}

        stored: list[dict[str, Any]] = []
        notes: list[str] = []

        for upload in files:
            raw_name = upload.filename or "upload"
            if not config.is_allowed(raw_name):
                raise HTTPException(
                    status_code=415,
                    detail=f"{raw_name}: file type not allowed",
                )

            data = await _read_bounded(upload, config.max_file_bytes)

            used += len(data)
            if used > config.max_thread_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Thread attachment quota exceeded",
                )

            name = unique_name(sanitise_filename(raw_name), taken)
            taken.add(name)

            result = await extract_best(name, data, config.max_inline_chars, extraction)
            text, complete = result.text, result.complete
            engine, degraded = result.engine, result.degraded
            path = f"{config.mount_path.rstrip('/')}/{name}"

            from agent.src.knowledge.transcribe import (
                MAX_INLINE_BYTES,
                is_media,
            )

            if is_media(name) and len(data) > MAX_INLINE_BYTES:
                from agent.src.knowledge.transcribe import (
                    TranscriptionUnavailable,
                    transcribe,
                )

                try:
                    text = await asyncio.to_thread(
                        transcribe, name, data, _orchestrator_model()
                    )
                    complete = True
                    engine, degraded = "transcription", ""
                    logger.info(
                        "Transcribed oversized media %s into %d characters",
                        name,
                        len(text),
                    )
                except TranscriptionUnavailable as exc:
                    raise HTTPException(status_code=413, detail=str(exc)) from None

            if text:
                existing[path] = added[path] = {"content": text, "encoding": "utf-8"}
            elif needs_base64(name):
                import base64

                existing[path] = added[path] = {
                    "content": base64.standard_b64encode(data).decode("ascii"),
                    "encoding": "base64",
                }
            else:
                existing[path] = added[path] = {
                    "content": (
                        f"[{suffix_or_file(name)} file, {len(data)} bytes — "
                        "stored but not readable as text]"
                    ),
                    "encoding": "utf-8",
                }

            _remember_for_retrieval(thread_id, name, path, text)

            stored.append(
                {
                    "filename": name,
                    "path": path,
                    "bytes": len(data),
                    "text_extracted": bool(text),
                    "truncated": not complete,
                    "engine": engine,
                    "degraded": degraded or None,
                }
            )
            notes.append(
                describe(
                    name,
                    len(data),
                    text,
                    complete,
                    engine=engine,
                    degraded=degraded,
                )
            )

        update = await client.post(
            f"/threads/{thread_id}/state",
            json={"values": {"files": added}, "assistant_id": assistant_id},
        )
        if update.status_code == 400 and "no associated graph" in update.text:
            await client.patch(
                f"/threads/{thread_id}",
                json={"metadata": {"graph_id": "agent", "assistant_id": assistant_id}},
            )
            update = await client.post(
                f"/threads/{thread_id}/state",
                json={"values": {"files": added}, "assistant_id": assistant_id},
            )
        if update.status_code not in (200, 201):
            logger.error("Attachment state update failed: %s", update.text[:200])
            raise HTTPException(status_code=502, detail="Could not store attachments")

    logger.info(
        "Stored %d attachment(s) on thread %s for %s", len(stored), thread_id, user_id
    )
    return {"attachments": stored, "summary": "\n".join(notes)}


class ExtractionStatusOut(BaseModel):
    """Which parser is in use, and can it be reached."""

    engine: str
    reachable: bool
    detail: str = ""
    fallback: bool = False
    handles: list[str] = []
    max_bytes: int = 0


@router.get("/attachments/extraction", responses={200: {"model": ExtractionStatusOut}})
async def extraction_status(request: Request) -> dict[str, Any]:
    """Which parser is in use, and can it actually be reached?"""
    await authenticated_user_id(request, reject_anonymous=True)

    from agent.src.attachments.engines import probe

    extraction = _extraction_config()
    ok, detail = await probe(extraction)
    return {
        "engine": extraction.engine,
        "reachable": ok,
        "detail": detail,
        "fallback": extraction.fallback,
        "handles": sorted(extraction.suffixes)
        if extraction.engine != "builtin"
        else [],
        "max_bytes": extraction.max_bytes,
    }


@router.get(
    "/threads/{thread_id}/attachments",
    responses={200: {"model": ThreadAttachmentsOut}},
)
async def list_attachments(thread_id: str, request: Request) -> dict[str, Any]:
    """What is already attached to this thread."""
    await authenticated_user_id(request, reject_anonymous=True)
    config = _config()

    import httpx

    from agent.src.settings import settings

    headers = {}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth

    async with httpx.AsyncClient(
        base_url=settings.loopback_base_url, headers=headers, timeout=30
    ) as client:
        state = await client.get(f"/threads/{thread_id}/state")
        if state.status_code != 200:
            raise HTTPException(status_code=404, detail="Thread not found")

        files = ((state.json() or {}).get("values") or {}).get("files") or {}

    prefix = config.mount_path.rstrip("/") + "/"
    return {
        "attachments": [
            {
                "filename": path[len(prefix) :],
                "path": path,
                "chars": len(
                    str(body.get("content", "")) if isinstance(body, dict) else body
                ),
            }
            for path, body in files.items()
            if path.startswith(prefix)
        ]
    }
