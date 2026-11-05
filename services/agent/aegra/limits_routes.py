"""Asking what you have left."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent.src.limits.report import describe_allowance
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/limits", tags=["limits"])


async def _who(request: Request) -> str:
    """Whose allowance this is."""
    from agent.aegra.auth_helpers import memory_user_id

    return await memory_user_id(request)


async def _teams_of(request: Request) -> tuple[str, ...]:
    """The teams the caller belongs to."""
    from agent.aegra.knowledge_routes import _teams_of as resolve

    return await resolve(request)


async def _spent_today(key: str) -> Decimal:
    """What `key` has spent today."""
    from agent.src.security.caller_spend import spent_today

    return await spent_today(key)


async def _spent_this_month(key: str) -> Decimal:
    """What `key` has spent this month."""
    from agent.src.security.caller_spend import spent_this_month

    return await spent_this_month(key)


class AllowanceOut(BaseModel):
    """What is left of an allowance, and whether it is nearly out."""

    model_config = {"extra": "allow"}

    spent: str = "0"
    limit: str | None = None
    remaining: str | None = None
    nearly_out: bool = False


class MyLimitsOut(BaseModel):
    """What this person has spent today, and what they may."""

    model_config = {"extra": "allow"}

    person: AllowanceOut
    team: AllowanceOut | None = None
    forecast: dict[str, Any] = {}
    unreadable: bool = False
    team_name: str | None = None


@router.get("/mine", responses={200: {"model": MyLimitsOut}})
async def my_allowance(request: Request) -> dict[str, Any]:
    """What this person has spent today, and what they may."""
    from agent.src.agent.config import agent_config

    allowance = agent_config.get_limits_config()
    who = await _who(request)
    teams = await _teams_of(request)

    unreadable = False
    try:
        person = await _spent_today(who)
        team = await _spent_today(f"team:{teams[0]}") if teams else Decimal("0")
        month = await _spent_this_month(who)
        month_team = (
            await _spent_this_month(f"team:{teams[0]}") if teams else Decimal("0")
        )
    except Exception as error:
        logger.warning("Could not read today's spend: %s", error)
        person = team = month = month_team = Decimal("0")
        unreadable = True

    found = describe_allowance(
        allowance=allowance,
        spent_by_person=person,
        spent_by_team=team,
        in_a_team=bool(teams),
        month_by_person=month,
        month_by_team=month_team,
    )
    found["unreadable"] = unreadable
    found["team_name"] = teams[0] if teams else None
    return found
