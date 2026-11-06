"""Speaking to the agent instead of typing."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.knowledge.transcribe import TranscriptionUnavailable, is_media
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/speech", tags=["speech"])

MAX_DICTATION_BYTES = settings.DICTATION_MAX_BYTES


def _dictation_enabled() -> bool:
    """Whether dictation is turned on for this deployment."""
    return bool(settings.DICTATION_ENABLED)


def _orchestrator_model() -> str:
    """The model the orchestrator is configured with."""
    from agent.aegra.attachment_routes import _orchestrator_model as configured

    return configured()


def _dictation_model() -> str:
    """The engine that hears the audio, named by the deployment or not."""
    return (settings.DICTATION_MODEL or "").strip() or _orchestrator_model()


def _to_text(filename: str, data: bytes) -> str:
    """Transcribe an uploaded audio file to text."""
    from agent.src.knowledge.transcribe import transcribe

    return transcribe(filename, data, _dictation_model(), for_dictation=True)


class DictationOut(BaseModel):
    """Whether this deployment will take dictation."""

    dictation: bool


class TranscriptOut(BaseModel):
    """The transcribed text."""

    text: str


@router.get("", responses={200: {"model": DictationOut}})
async def speech_capabilities() -> dict[str, Any]:
    """What this deployment will do with speech, so the UI can ask first."""
    return {"dictation": _dictation_enabled()}


@router.post("/transcribe", responses={200: {"model": TranscriptOut}})
async def transcribe_dictation(
    request: Request, audio: UploadFile = File(...)
) -> dict[str, str]:
    """Turn a recording into text for the person to read before sending."""
    if not _dictation_enabled():
        raise HTTPException(status_code=404, detail="Not Found")

    await authenticated_user_id(request, reject_anonymous=True)

    filename = audio.filename or "dictation.webm"
    if not is_media(filename):
        raise HTTPException(status_code=415, detail=f"{filename} is not a recording")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="The recording was empty")
    if len(data) > MAX_DICTATION_BYTES:
        raise HTTPException(
            status_code=413,
            detail="That recording is too long to dictate. Attach it as a file instead.",
        )

    try:
        said = await asyncio.to_thread(_to_text, filename, data)
    except TranscriptionUnavailable as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    logger.info("Dictation transcribed, %d bytes of audio dropped", len(data))
    return {"text": (said or "").strip()}
