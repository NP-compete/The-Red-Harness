"""Optional external document-extraction engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

if TYPE_CHECKING:
    from agent.src.attachments.config import ExtractionConfig

logger = get_python_logger()

PAGE_BREAK = "\f"

SUSPECT_CHARS = settings.ATTACHMENT_SUSPECT_CHARS


class ExtractionUnavailable(RuntimeError):
    """The engine could not be used. Always caught — never surfaced."""


@dataclass(frozen=True)
class RemoteResult:
    """Extracted text and the engine that produced it."""

    text: str
    engine: str


async def extract_remote(
    filename: str, data: bytes, config: ExtractionConfig
) -> RemoteResult:
    """Extract via the configured engine."""
    engine = config.engine
    if engine == "docling":
        text = await _docling(filename, data, config)
    elif engine == "tika":
        text = await _tika(filename, data, config)
    else:
        raise ExtractionUnavailable(f"unknown extraction engine {engine!r}")

    if not text.strip():
        raise ExtractionUnavailable(f"{engine} returned no text")
    return RemoteResult(text=text, engine=engine)


async def _docling(filename: str, data: bytes, config: ExtractionConfig) -> str:
    """Docling's `/v1/convert/file`, which returns markdown plus JSON."""
    headers = {"X-Api-Key": config.api_key} if config.api_key else {}

    form = {
        "image_export_mode": "placeholder",
        "md_page_break_placeholder": PAGE_BREAK,
        "to_formats": "md",
        **{k: str(v) for k, v in (config.params or {}).items()},
    }

    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                f"{config.url.rstrip('/')}/v1/convert/file",
                files={"files": (filename, data, _mime(filename))},
                data=form,
                headers=headers,
            )
    except Exception as exc:
        raise ExtractionUnavailable(f"docling unreachable: {exc}") from exc

    if response.status_code >= 400:
        raise ExtractionUnavailable(
            f"docling returned {response.status_code}: {_detail(response)}"
        )

    try:
        body = response.json()
    except Exception as exc:
        raise ExtractionUnavailable(f"docling returned non-JSON: {exc}") from exc

    status = str(body.get("status") or "").lower()
    if status in ("failure", "skipped"):
        errors = "; ".join(
            filter(None, (e.get("error_message") for e in body.get("errors") or []))
        )
        raise ExtractionUnavailable(
            f"docling conversion {status}: {errors or 'no error message'}"
        )

    document = body.get("document") or {}
    return str(document.get("md_content") or "")


async def _tika(filename: str, data: bytes, config: ExtractionConfig) -> str:
    """Tika's `PUT /tika`, asking for plain text."""
    headers = {
        "Accept": "text/plain",
        "Content-Type": _mime(filename),
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.put(
                f"{config.url.rstrip('/')}/tika", content=data, headers=headers
            )
    except Exception as exc:
        raise ExtractionUnavailable(f"tika unreachable: {exc}") from exc

    if response.status_code >= 400:
        raise ExtractionUnavailable(
            f"tika returned {response.status_code}: {_detail(response)}"
        )
    return str(response.text)


def _mime(filename: str) -> str:
    import mimetypes

    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])[:200]
    except Exception:
        pass
    return (response.text or response.reason_phrase or "")[:200]


async def probe(config: ExtractionConfig) -> tuple[bool, str]:
    """Is the configured engine reachable? Returns `(ok, detail)`."""
    if config.engine == "builtin":
        return True, "built-in parsers"
    if not config.url:
        return False, f"{config.engine} selected but extraction.url is unset"

    path = "/health" if config.engine == "docling" else "/tika"
    try:
        async with httpx.AsyncClient(timeout=min(config.timeout_seconds, 10)) as client:
            response = await client.get(f"{config.url.rstrip('/')}{path}")
    except Exception as exc:
        return False, f"unreachable: {exc}"
    if response.status_code >= 400:
        return False, f"returned {response.status_code}"
    return True, f"{config.engine} reachable"
