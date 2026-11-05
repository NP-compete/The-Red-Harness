"""Work the person does not wait for, as something the model can call."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.src.token_budget.identity import resolve_user_id
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

WORK_TOOL = "work_in_background"
LIST_TOOL = "list_background_work"

ASSISTANT = "agent"

_NO_IDENTITY = (
    "I could not work out who to do this for, so I have not started "
    "anything. This usually means the request arrived without a "
    "signed-in user."
)


def _sessions() -> Any:
    from aegra_api.core.orm import get_session_maker

    return get_session_maker()


def _as_user(who: str) -> Any:
    """The identity the run is created under."""
    from aegra_api.models import User

    return User(identity=who, display_name=who, is_authenticated=True)


async def _start(instruction: str) -> str:
    who = resolve_user_id()
    if not who:
        return _NO_IDENTITY

    from aegra_api.models import RunCreate
    from aegra_api.services.run_preparation import _prepare_run

    from agent.src.threads.owned import create_owned_thread, title_from

    try:
        async with _sessions()() as session:
            thread_id = await create_owned_thread(
                session,
                owner=who,
                title=title_from(instruction),
                extra={"background": True},
            )
            request = RunCreate(
                assistant_id=ASSISTANT,
                input={"messages": [{"role": "human", "content": instruction}]},
            )
            _run_id, run, _job = await _prepare_run(
                session,
                thread_id,
                request,
                _as_user(who),
                initial_status="pending",
            )
            await session.commit()
    except Exception as error:  # noqa: BLE001 — the model can act on the text
        logger.warning("Background work could not be started: %s", error)
        return f"I could not start that in the background just now: {error}"

    return (
        f"Started. I am working on it in a conversation called "
        f"'{title_from(instruction)}' — its id is {thread_id}, and the "
        f"run is {run.run_id}. Open that conversation to watch it or "
        f"read the answer when it is done; you do not need to wait here."
    )


async def _list() -> str:
    who = resolve_user_id()
    if not who:
        return _NO_IDENTITY

    from aegra_api.core.orm import Run as RunORM
    from aegra_api.core.orm import Thread as ThreadORM
    from sqlalchemy import select

    try:
        async with _sessions()() as session:
            threads = (
                await session.scalars(select(ThreadORM).where(ThreadORM.user_id == who))
            ).all()
            mine = [
                t for t in threads if (t.metadata_json or {}).get("background") is True
            ]
            if not mine:
                return "Nothing is running in the background for you."

            lines = []
            for thread in mine:
                runs = (
                    await session.scalars(
                        select(RunORM).where(RunORM.thread_id == thread.thread_id)
                    )
                ).all()
                latest = max(runs, key=lambda r: r.created_at) if runs else None
                name = (thread.metadata_json or {}).get("thread_name") or "untitled"
                state = latest.status if latest is not None else "not started"
                lines.append(f"- {name} — {state} (conversation {thread.thread_id})")
            return "Background work:\n" + "\n".join(lines)
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not list background work: %s", error)
        return f"I could not read your background work just now: {error}"


class _Work(BaseModel):
    instruction: str = Field(
        description=(
            "What to do, written as you would say it to someone taking the "
            "job away with them. It must stand alone: the background run "
            "starts in a new conversation and cannot see this one."
        )
    )


def build_background_tools() -> list[StructuredTool]:
    """The two tools, or none when the dependency is unavailable."""
    try:
        from aegra_api.core.orm import get_session_maker  # noqa: F401
    except Exception:  # noqa: BLE001 — no Aegra, no background work
        return []

    return [
        StructuredTool.from_function(
            coroutine=_start,
            name=WORK_TOOL,
            description=(
                "Start a long piece of work that continues after this "
                "conversation. Use it when the answer would take minutes "
                "and the person should not have to sit and wait. The work "
                "runs in its own conversation, which they can open later. "
                "Needs approval, because it keeps running when they leave."
            ),
            args_schema=_Work,
        ),
        StructuredTool.from_function(
            coroutine=_list,
            name=LIST_TOOL,
            description=(
                "List the background work running for this person and how "
                "each piece is getting on."
            ),
        ),
    ]
