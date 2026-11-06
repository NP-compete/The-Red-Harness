"""The ways of answering a reader may choose between."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.src.agent.reasoning_profiles import worth_offering
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["reasoning"])


def _routing_config() -> Any:
    """The routing configuration as plain data, or nothing."""
    try:
        from agent.src.routing.config import load_router_config

        return load_router_config().model_dump()
    except Exception:
        logger.debug("Could not read the routing configuration", exc_info=True)
        return {}


class ReasoningProfileOut(BaseModel):
    """One reasoning profile and the effort it asks for."""

    name: str
    effort: str = ""


class ReasoningProfilesOut(BaseModel):
    """Every reasoning profile this deployment offers."""

    profiles: list[ReasoningProfileOut]


async def _offered_to(request: Request) -> bool:
    """Whether this person has turned profiles on (CFG-1)."""
    try:
        from agent.aegra.feature_routes import FLAG_REASONING_PROFILES, settled_for

        return await settled_for(request, FLAG_REASONING_PROFILES)
    except Exception:
        logger.debug("Could not settle the reasoning-profiles flag", exc_info=True)
        return False


@router.get("/reasoning-profiles", responses={200: {"model": ReasoningProfilesOut}})
async def list_reasoning_profiles(request: Request) -> JSONResponse:
    """Name and effort only, and an empty list when there is no choice."""
    offered = worth_offering(_routing_config()) if await _offered_to(request) else []
    return JSONResponse(
        content={
            "profiles": [{"name": one.name, "effort": one.effort} for one in offered]
        }
    )
