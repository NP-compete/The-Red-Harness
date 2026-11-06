"""What this deployment has interposed on its runs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from agent.src.infrastructure.extensions import declared_extension

router = APIRouter(tags=["extensions"])


def _declared() -> list[Any]:
    """Every extension declared in the middleware config."""
    from agent.src.agent.config import agent_config

    return list(agent_config.get_middleware_config().defaults.extra or [])


def _timing(path: str) -> dict[str, Any] | None:
    """The timing summary for the extension at `path`, if there is one."""
    from agent.src.infrastructure import extension_metrics

    return extension_metrics.timing.summary(path)


def _describe_remote(entry: dict[str, Any]) -> dict[str, Any]:
    """An extension that runs in its own process (E37-T3)."""
    from agent.src.infrastructure.remote_extension import declared_remote

    try:
        extension = declared_remote(entry)
    except ValueError as error:
        return {
            "path": str(entry.get("url") or entry),
            "where": "remote",
            "required": True,
            "loaded": False,
            "problem": str(error),
            "timing": None,
        }
    return {
        "path": extension.url,
        "where": "remote",
        "required": extension.required,
        "loaded": not extension.unavailable(),
        "problem": (
            "it has been failing and is being left alone for now"
            if extension.unavailable()
            else ""
        ),
        "timeout_seconds": extension.timeout_seconds,
        "timing": None,
    }


def _describe(entry: Any) -> dict[str, Any]:
    """One declared extension as a response body."""
    if isinstance(entry, dict) and entry.get("url"):
        return _describe_remote(entry)
    try:
        extension = declared_extension(entry)
    except ValueError as error:
        return {
            "path": str(entry),
            "where": "in-process",
            "required": True,
            "loaded": False,
            "problem": str(error),
            "timing": None,
        }

    loaded, problem = extension.status()
    return {
        "path": extension.path,
        "where": "in-process",
        "required": extension.required,
        "loaded": loaded,
        "problem": problem,
        "timing": _timing(extension.path),
    }


class ExtensionOut(BaseModel):
    """One declared extension, and whether it is in the path."""

    model_config = {"extra": "allow"}

    name: str = ""


class ExtensionsOut(BaseModel):
    """Every declared extension."""

    extensions: list[ExtensionOut]


@router.get("/extensions", responses={200: {"model": ExtensionsOut}})
async def list_extensions() -> dict[str, Any]:
    """Every declared extension, and whether it is in the path."""
    return {"extensions": [_describe(entry) for entry in _declared()]}
