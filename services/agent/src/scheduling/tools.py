"""Scheduling, as something the model can call."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.src.token_budget.identity import resolve_user_id
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

SCHEDULE_TOOL = "schedule_task"
LIST_TOOL = "list_scheduled_tasks"
CANCEL_TOOL = "cancel_scheduled_task"

ASSISTANT = "agent"

_NO_IDENTITY = (
    "I could not work out who to schedule this for, so I have not "
    "scheduled anything. This usually means the request arrived without "
    "a signed-in user."
)


class ScheduleInput(BaseModel):
    """Arguments for scheduling a recurring task."""

    schedule: str = Field(
        description=(
            "A five-field cron expression in UTC: minute hour day-of-month "
            "month day-of-week. '0 8 * * *' is every day at 08:00, "
            "'*/15 * * * *' is every fifteen minutes, '0 9 * * 1' is Mondays "
            "at 09:00. Minute is the finest granularity; anything shorter "
            "cannot be scheduled."
        )
    )
    instruction: str = Field(
        description=(
            "What to do each time this fires, written as you would say it to "
            "an assistant with no memory of this conversation. It starts a "
            "fresh thread, so include whatever context the task needs."
        )
    )
    timezone: str = Field(
        default="",
        description=(
            "An IANA timezone such as 'Europe/London' to read the schedule "
            "in. Leave empty for UTC."
        ),
    )


class CancelInput(BaseModel):
    """Arguments for cancelling a scheduled task."""

    task_id: str = Field(description="The id from list_scheduled_tasks.")


def _service(session: Any) -> Any:
    """The cron service bound to this session."""
    from aegra_api.services.cron_service import CronService
    from aegra_api.services.langgraph_service import get_langgraph_service

    return CronService(session, get_langgraph_service())


def _sessions() -> Any:
    """The session maker."""
    from aegra_api.core.orm import get_session_maker

    return get_session_maker()


def _describe(cron: Any) -> str:
    """One scheduled task as a line the model can read."""
    instruction = ""
    payload = getattr(cron, "payload", None) or {}
    messages = (payload.get("input") or {}).get("messages") or []
    if messages:
        instruction = str(messages[0].get("content", ""))
    state = "" if getattr(cron, "enabled", True) else " (paused)"
    where = f" Its runs are in conversation {cron.thread_id}." if cron.thread_id else ""
    return (
        f"{cron.cron_id} — '{cron.schedule}', next at "
        f"{cron.next_run_date}{state}: {instruction}{where}"
    )


async def _home_thread(session: Any, who: str, instruction: str) -> str:
    """A conversation for this schedule to keep its runs in."""
    from agent.src.threads.owned import create_owned_thread, title_from

    return await create_owned_thread(
        session,
        owner=who,
        title=title_from(instruction),
        extra={"scheduled": True},
    )


def _title(instruction: str) -> str:
    """A short title for a scheduled instruction."""
    from agent.src.threads.owned import title_from

    return title_from(instruction)


async def _schedule(schedule: str, instruction: str, timezone: str = "") -> str:
    """Schedule a recurring task for the current user."""
    who = resolve_user_id()
    if not who:
        return _NO_IDENTITY

    from aegra_api.models.crons import CronCreate, CronUpdate
    from fastapi import HTTPException

    try:
        request = CronCreate(
            assistant_id=ASSISTANT,
            schedule=schedule,
            input={"messages": [{"role": "human", "content": instruction}]},
            timezone=timezone or None,
            enabled=False,
        )
    except Exception as error:
        return f"That schedule was not accepted: {error}"

    try:
        async with _sessions()() as session:
            service = _service(session)
            thread_id = await _home_thread(session, who, instruction)
            cron = await service.create_cron(request, who, thread_id=thread_id)
            cron = await service.update_cron(
                cron.cron_id, CronUpdate(enabled=True), who
            )
    except HTTPException as refused:
        return f"I could not set that up: {refused.detail}"
    except Exception as error:
        logger.warning("Scheduling failed: %s", error)
        return f"I could not set that up just now: {error}"

    where = f" ({timezone})" if timezone else " (UTC)"
    return (
        f"Scheduled. It runs on '{schedule}'{where}, first at "
        f"{cron.next_run_date}, and every run will appear in a "
        f"conversation called '{_title(instruction)}'. Its id is "
        f"{cron.cron_id}, which cancel_scheduled_task takes."
    )


async def _list() -> str:
    """The current user's scheduled tasks."""
    who = resolve_user_id()
    if not who:
        return _NO_IDENTITY

    from aegra_api.models.crons import CronSearchRequest

    try:
        async with _sessions()() as session:
            found = await _service(session).search_crons(
                CronSearchRequest(limit=50), who
            )
    except Exception as error:
        logger.warning("Listing schedules failed: %s", error)
        return f"I could not read the schedule list just now: {error}"

    if not found:
        return "Nothing is scheduled."
    return "\n".join(_describe(cron) for cron in found)


async def _cancel(task_id: str) -> str:
    """Cancel one of the current user's scheduled tasks."""
    who = resolve_user_id()
    if not who:
        return _NO_IDENTITY

    from fastapi import HTTPException

    try:
        async with _sessions()() as session:
            await _service(session).delete_cron(task_id, who)
    except HTTPException as refused:
        return f"I could not cancel that: {refused.detail}"
    except Exception as error:
        logger.warning("Cancelling a schedule failed: %s", error)
        return f"I could not cancel that just now: {error}"

    return f"Cancelled {task_id}. It will not run again."


def build_schedule_tools() -> list[Any]:
    """The scheduling tools, or nothing when the scheduler is off."""
    try:
        from aegra_api.settings import settings as aegra_settings

        if not aegra_settings.cron.CRON_ENABLED:
            return []
    except Exception as error:
        logger.warning("Scheduling tools unavailable: %s", error)
        return []

    return [
        StructuredTool.from_function(
            coroutine=_schedule,
            name=SCHEDULE_TOOL,
            description=(
                "Schedule yourself to do something later, on a repeating "
                "cron schedule. Each firing starts a fresh conversation with "
                "the instruction you give, so write it to stand alone. "
                "Minute is the finest granularity available."
            ),
            args_schema=ScheduleInput,
        ),
        StructuredTool.from_function(
            coroutine=_list,
            name=LIST_TOOL,
            description=(
                "List what this person already has scheduled, with the id "
                "needed to cancel each one."
            ),
        ),
        StructuredTool.from_function(
            coroutine=_cancel,
            name=CANCEL_TOOL,
            description="Cancel a scheduled task by its id.",
            args_schema=CancelInput,
        ),
    ]
