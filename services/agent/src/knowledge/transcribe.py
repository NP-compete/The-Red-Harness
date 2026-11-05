"""Turn audio and video into text so it can be indexed."""

from __future__ import annotations

import base64
import mimetypes

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_AUDIO = {"mp3", "wav", "ogg", "m4a", "aac", "flac"}
_VIDEO = {"mp4", "mov", "webm", "avi", "mkv"}

MAX_INLINE_BYTES = settings.TRANSCRIBE_MAX_INLINE_BYTES

_TIMEOUT_SECONDS = settings.TRANSCRIBE_TIMEOUT_SECONDS


class TranscriptionUnavailable(RuntimeError):
    """The file cannot be transcribed, with a reason worth showing."""


def is_media(filename: str) -> bool:
    """Does this filename look like audio or video needing transcription?"""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return suffix in _AUDIO or suffix in _VIDEO


_FOR_INDEXING = (
    "Transcribe this recording verbatim. Include speaker labels where "
    "you can tell them apart, and timestamps at natural section "
    "boundaries. Output only the transcript."
)
_FOR_DICTATION = (
    "Transcribe this recording verbatim as plain prose. No speaker "
    "labels, no times, no headings. Output only what was said."
)


def transcribe(
    filename: str, data: bytes, model_name: str, *, for_dictation: bool = False
) -> str:
    """Transcribe audio or video to text."""
    mime = mimetypes.guess_type(filename)[0]
    if not mime:
        suffix = filename.rsplit(".", 1)[-1].lower()
        mime = f"{'audio' if suffix in _AUDIO else 'video'}/{suffix}"

    from langchain_core.messages import HumanMessage

    from agent.src.agent.llm import create_model

    uploaded_uri: str | None = None
    if len(data) > MAX_INLINE_BYTES:
        from agent.src.knowledge.media_upload import (
            MediaUploadError,
            upload_media,
        )

        try:
            uri = upload_media(filename, data)
        except MediaUploadError as exc:
            raise TranscriptionUnavailable(str(exc)) from exc
        uploaded_uri = uri
        media_block: dict = {"type": "media", "file_uri": uri, "mime_type": mime}
        logger.info("Transcribing %s via uploaded file %s", filename, uri)
    else:
        media_block = {
            "type": "media",
            "data": base64.standard_b64encode(data).decode("ascii"),
            "mime_type": mime,
        }

    model = create_model(model_name, temperature=0.0, max_output_tokens=8192)

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": _FOR_DICTATION if for_dictation else _FOR_INDEXING,
            },
            media_block,
        ]
    )

    try:
        result = model.invoke([message], timeout=_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("Transcription failed for %s: %s", filename, exc)
        raise TranscriptionUnavailable(
            f"{filename}: could not be transcribed ({type(exc).__name__})"
        ) from exc
    finally:
        if uploaded_uri:
            from agent.src.knowledge.media_upload import delete_media

            delete_media(uploaded_uri)

    content = result.content
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    text = str(content or "").strip()

    if not text:
        raise TranscriptionUnavailable(
            f"{filename}: the recording produced no transcript — it may be "
            "silent or have no speech"
        )
    return text
