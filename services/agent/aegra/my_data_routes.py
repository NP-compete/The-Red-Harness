"""Taking a copy of what is held about you, and asking for it to go."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent.src.security.data_deletion import plan_deletion
from agent.src.security.data_export import build_export
from agent.src.security.subject_request import Kind, Store, plan_request
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/me", tags=["my-data"])


async def _who(request: Request) -> str:
    """The same name every other page and run uses."""
    from agent.aegra.auth_helpers import memory_user_id

    return await memory_user_id(request)


def _held_about(subject: str) -> dict[str, list[dict[str, Any]]]:
    """Everything the stores this can reach hold about one person."""
    held: dict[str, list[dict[str, Any]]] = {}

    try:
        from agent.src.knowledge.scopes import Scope
        from agent.src.knowledge.store import session_store

        held["documents"] = [
            {
                "id": document.id,
                "owner": subject,
                "title": document.title,
                "text": document.text,
                "scope": document.scope.value,
            }
            for document in session_store().documents_in(
                scope=Scope.USER, owner=subject
            )
        ]
    except Exception as error:
        logger.warning("Could not collect documents for %s: %s", subject, error)

    try:
        from agent.src.knowledge.artifacts import Owner, session_artifacts

        store = session_artifacts()
        owner = Owner(subject=subject, teams=())
        held["artifacts"] = [
            {"id": key, "owner": subject, "value": store.get(owner, key=key)}
            for key in store.keys(owner)
        ]
    except Exception as error:
        logger.warning("Could not collect artifacts for %s: %s", subject, error)

    return held


def _remove(subject: str, section: str, ids: list[str]) -> None:
    """Take these away. Raises, so a failure is reported not assumed."""
    if section == "documents":
        from agent.src.knowledge.scopes import Viewer
        from agent.src.knowledge.store import session_store

        store = session_store()
        viewer = Viewer(subject=subject, teams=(), thread_id=None)
        for one in ids:
            store.remove(one, viewer=viewer)
    elif section == "artifacts":
        from agent.src.knowledge.artifacts import Owner, session_artifacts

        artifacts = session_artifacts()
        owner = Owner(subject=subject, teams=())
        for one in ids:
            artifacts.delete(owner, key=one)


_KNOWN_STORES = ("documents", "artifacts", "memory")

_WHY_MISSING = {
    "memory": (
        "not included here; each remembered fact is listed and removable "
        "on the personalisation page"
    ),
}


def _memory_repository() -> Any:
    """The store holding a person's saved facts, or nothing."""
    try:
        from agent.src.personalization.repository import PersonalizationRepository
        from agent.src.settings import settings

        return PersonalizationRepository(settings.database_uri)
    except Exception:
        logger.warning("Could not reach the memory store", exc_info=True)
        return None


async def _collect_async(subject: str) -> dict[str, list[dict[str, Any]]]:
    """Everything held about one person, including their memories."""
    held = _held_about(subject)

    repository = _memory_repository()
    if repository is None:
        return held

    try:
        memories = await repository.list_memories(subject)
        held["memories"] = [
            {
                "id": str(getattr(one, "id", "")),
                "owner": subject,
                "thread_id": getattr(one, "thread_id", None),
                "text": getattr(one, "content", ""),
            }
            for one in memories
        ]
    except Exception:
        logger.warning("Could not collect memories for %s", subject, exc_info=True)

    return held


async def _remove_async(subject: str, section: str, ids: list[str]) -> None:
    """Delete from whichever store holds this section."""
    if section != "memories":
        _remove(subject, section, ids)
        return

    repository = _memory_repository()
    if repository is None:
        return

    import uuid as _uuid

    for one in ids:
        try:
            await repository.delete_memory(subject, _uuid.UUID(str(one)))
        except ValueError:
            await repository.delete_memory(subject, one)
        except Exception:
            logger.warning("Could not delete memory %s", one, exc_info=True)


def _missing_from(held: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    """Stores that exist and did not come back."""
    return {
        name: _WHY_MISSING.get(name, "could not be read just now")
        for name in _KNOWN_STORES
        if name not in held
    }


def _stores(held: dict[str, list[dict[str, Any]]]) -> tuple[Store, ...]:
    """The stores a subject request has to look in, given what is held."""
    return (
        Store(
            name="documents",
            holds_data=bool(held.get("documents")),
            on_legal_hold=False,
            deletable=True,
        ),
        Store(
            name="artifacts",
            holds_data=bool(held.get("artifacts")),
            on_legal_hold=False,
            deletable=True,
        ),
        Store(
            name="memory",
            holds_data=True,
            on_legal_hold=False,
            deletable=False,
        ),
    )


def _now() -> datetime:
    """The current UTC time."""
    return datetime.now(timezone.utc)


class MyDataExportOut(BaseModel):
    """A subject's exported data, and anything withheld."""

    subject: str
    sections: dict[str, Any] = {}
    counts: dict[str, int] = {}
    made_at: str | None = None
    complete: bool
    withheld: dict[str, str] = {}


class DeletionPreviewOut(BaseModel):
    """What deleting a subject's data would remove and keep."""

    subject: str
    delete: dict[str, Any] = {}
    kept: dict[str, Any] = {}
    retained: dict[str, Any] = {}
    counts: dict[str, int] = {}
    notes: list[str] = []
    not_included: dict[str, str] = {}


class MyDataDeletedOut(BaseModel):
    """What was deleted, kept, retained, and what failed."""

    subject: str
    counts: dict[str, int] = {}
    kept: dict[str, Any] = {}
    retained: dict[str, Any] = {}
    failed: dict[str, str] = {}
    notes: list[str] = []
    not_included: dict[str, str] = {}


@router.get("/export", responses={200: {"model": MyDataExportOut}})
async def export_my_data(request: Request) -> dict[str, Any]:
    """A copy of what is held, and a list of what is not in it."""
    subject = await _who(request)
    held = await _collect_async(subject)

    found = build_export(
        subject=subject, held=held, made_at=_now().isoformat(timespec="seconds")
    )

    plan = plan_request(Kind.EXPORT, stores=_stores(held), now=_now())
    withheld = {**plan.withheld, **_missing_from(held)}

    return {
        "subject": found.subject,
        "sections": found.sections,
        "counts": found.counts,
        "made_at": found.made_at,
        "complete": not withheld,
        "withheld": withheld,
    }


@router.get("/deletion-preview", responses={200: {"model": DeletionPreviewOut}})
async def preview_deletion(request: Request) -> dict[str, Any]:
    """What removing everything would take, before it takes it."""
    subject = await _who(request)
    plan = plan_deletion(subject=subject, held=await _collect_async(subject))

    return {
        "subject": plan.subject,
        "delete": plan.delete,
        "kept": plan.kept,
        "retained": plan.retained,
        "counts": plan.counts,
        "notes": plan.notes,
        "not_included": _missing_from(await _collect_async(subject)),
    }


@router.delete("/data", responses={200: {"model": MyDataDeletedOut}})
async def delete_my_data(request: Request) -> dict[str, Any]:
    """Remove what can be removed, and say what could not."""
    subject = await _who(request)
    plan = plan_deletion(subject=subject, held=await _collect_async(subject))

    failed: dict[str, str] = {}
    for section, ids in plan.delete.items():
        if not ids:
            continue
        try:
            await _remove_async(subject, section, ids)
        except Exception as error:
            logger.error("Could not remove %s for %s: %s", section, subject, error)
            failed[section] = str(error)

    return {
        "subject": subject,
        "counts": {
            section: len(ids)
            for section, ids in plan.delete.items()
            if section not in failed
        },
        "kept": plan.kept,
        "retained": plan.retained,
        "failed": failed,
        "notes": plan.notes,
        "not_included": _missing_from(await _collect_async(subject)),
    }
