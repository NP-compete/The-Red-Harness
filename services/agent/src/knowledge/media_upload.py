"""Hand large media to Gemini via Cloud Storage."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any

from agent.src.knowledge.transcribe import MAX_INLINE_BYTES
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_FILE_API_BYTES = settings.MEDIA_MAX_FILE_API_BYTES

_PREFIX = settings.MEDIA_UPLOAD_PREFIX

_PROCESSING_TIMEOUT = settings.MEDIA_PROCESSING_TIMEOUT_SECONDS
_POLL_SECONDS = settings.MEDIA_POLL_SECONDS


class MediaUploadError(RuntimeError):
    """The file could not be made available to the model."""


def _bucket_name() -> str | None:
    import os

    return os.environ.get("MEDIA_BUCKET") or None


def _client() -> Any:
    from google.cloud import storage

    from agent.src.settings import settings
    from agent.utils.google_creds import get_service_account_credentials

    credentials, project = get_service_account_credentials()
    return storage.Client(
        project=settings.GOOGLE_CLOUD_PROJECT or project, credentials=credentials
    )


def upload_media(filename: str, data: bytes) -> str:
    """Upload bytes and return a URI the model can reference."""
    if len(data) > MAX_FILE_API_BYTES:
        raise MediaUploadError(
            f"{filename}: {len(data) // 1024 // 1024} MB exceeds the "
            f"{MAX_FILE_API_BYTES // 1024 // 1024 // 1024} GB upload limit"
        )

    bucket_name = _bucket_name()
    if not bucket_name:
        size_mb = len(data) // 1024 // 1024
        raise MediaUploadError(
            f"{filename}: {size_mb} MB is larger than the model accepts in one "
            f"request ({MAX_INLINE_BYTES // 1024 // 1024} MB). Larger media "
            "needs a Cloud Storage bucket — set MEDIA_BUCKET — or a shorter clip."
        )

    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    try:
        client = _client()
    except Exception as exc:
        raise MediaUploadError(f"Could not reach Cloud Storage: {exc}") from exc

    import uuid

    blob_name = f"{_PREFIX}/{uuid.uuid4().hex}/{Path(filename).name}"

    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data, content_type=mime)
    except Exception as exc:
        logger.warning("Media upload failed for %s: %s", filename, exc)
        raise MediaUploadError(
            f"{filename}: could not be uploaded to gs://{bucket_name} "
            f"({type(exc).__name__})"
        ) from exc

    uri = f"gs://{bucket_name}/{blob_name}"
    logger.info("Uploaded %s (%d bytes) to %s", filename, len(data), uri)
    return uri


def _await_active(client: Any, uploaded: Any, filename: str) -> str:
    """Block until the service has processed the upload."""
    deadline = time.monotonic() + _PROCESSING_TIMEOUT
    current = uploaded

    while time.monotonic() < deadline:
        state = str(getattr(current.state, "name", current.state) or "").upper()

        if state == "ACTIVE":
            return str(current.uri)
        if state == "FAILED":
            raise MediaUploadError(
                f"{filename}: the service could not process this file — "
                "it may be corrupt or in an unsupported codec"
            )

        time.sleep(_POLL_SECONDS)
        current = client.files.get(name=current.name)

    raise MediaUploadError(
        f"{filename}: still processing after {_PROCESSING_TIMEOUT}s — "
        "try a shorter clip"
    )


def delete_media(uri: str) -> None:
    """Best-effort cleanup of an uploaded object."""
    try:
        if not uri.startswith("gs://"):
            return
        bucket_name, _, blob_name = uri[5:].partition("/")
        _client().bucket(bucket_name).blob(blob_name).delete()
    except Exception:
        logger.debug("Could not delete uploaded media %s", uri, exc_info=True)
