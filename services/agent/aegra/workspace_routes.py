"""Files the agent wrote for this person, and a way to reach them."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from agent.aegra.auth_helpers import memory_user_id
from agent.src.memory.instructions import is_memory_store_key
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix="/workspace", tags=["workspace"])


async def _get_store() -> Any:
    from agent.aegra.personalization_routes import _get_store as shared

    return await shared()


def _filesystem_routes() -> dict[str, str]:
    from agent.src.agent.config import agent_config

    try:
        backend = agent_config.get_filesystem_config().backend
    except Exception:
        logger.debug("Could not read the filesystem routes", exc_info=True)
        return {}
    return dict(getattr(backend, "routes", None) or {})


def _store_route() -> str:
    """The path prefix under which the agent reaches these files."""
    routes = {
        path: target
        for path, target in _filesystem_routes().items()
        if target == "store" and "memor" not in path
    }
    for path in sorted(routes, key=len, reverse=True):
        return path
    return ""


def _as_path(key: str) -> str:
    """The key, named the way the agent names it."""
    bare = "/" + key.lstrip("/")
    route = _store_route()
    if not route or bare.startswith(route):
        return bare
    return route.rstrip("/") + bare


async def _namespaces(user_id: str) -> list[tuple[str, ...]]:
    from agent.aegra.personalization_routes import _candidate_namespaces

    return await _candidate_namespaces(user_id)


class WorkspaceFileOut(BaseModel):
    """One file in a workspace."""

    path: str
    bytes: int = 0
    modified: str = ""


class WorkspaceFilesOut(BaseModel):
    """The files in a workspace."""

    files: list[WorkspaceFileOut]


class WorkspaceFileContentOut(BaseModel):
    """The contents of a single workspace file."""

    path: str
    content: str = ""


@router.get("/files", responses={200: {"model": WorkspaceFilesOut}})
async def list_workspace_files(request: Request) -> dict[str, Any]:
    """Everything in this person's store that is not their memory file."""
    user_id = await memory_user_id(request)
    store = await _get_store()

    found: dict[str, dict[str, Any]] = {}
    for namespace in await _namespaces(user_id):
        try:
            items = await store.asearch(namespace, limit=200)
        except Exception:
            logger.debug("Could not search %s", namespace, exc_info=True)
            continue

        for item in items:
            key = str(getattr(item, "key", "") or "")
            if not key or is_memory_store_key(key):
                continue
            value = getattr(item, "value", None) or {}
            content = value.get("content") if isinstance(value, dict) else None
            found.setdefault(
                key,
                {
                    "path": _as_path(key),
                    "bytes": len(content.encode("utf-8"))
                    if isinstance(content, str)
                    else 0,
                    "modified": str(
                        getattr(item, "updated_at", None)
                        or getattr(item, "created_at", None)
                        or ""
                    ),
                },
            )

    return {"files": sorted(found.values(), key=lambda f: f["path"])}


async def _find(user_id: str, path: str) -> tuple[Any, tuple[str, ...], str]:
    """The stored item for a path, the namespace holding it, and its key."""
    from fastapi import HTTPException

    store = await _get_store()
    asked = "/" + path.strip().lstrip("/")
    route = _store_route()
    wanted = asked
    if route and asked.startswith(route):
        wanted = "/" + asked[len(route) :].lstrip("/")

    for namespace in await _namespaces(user_id):
        try:
            items = await store.asearch(namespace, limit=200)
        except Exception:
            logger.debug("Could not search %s", namespace, exc_info=True)
            continue

        for item in items:
            key = str(getattr(item, "key", "") or "")
            if is_memory_store_key(key) or "/" + key.lstrip("/") != wanted:
                continue
            return item, namespace, key

    raise HTTPException(status_code=404, detail=f"No such file: {wanted}")


@router.get("/files/{path:path}", responses={200: {"model": WorkspaceFileContentOut}})
async def read_workspace_file(path: str, request: Request) -> dict[str, Any]:
    """One file's contents, for reading rather than editing."""
    item, _namespace, key = await _find(await memory_user_id(request), path)
    value = getattr(item, "value", None) or {}
    content = value.get("content") if isinstance(value, dict) else ""
    return {
        "path": _as_path(key),
        "content": content if isinstance(content, str) else "",
    }


@router.delete("/files/{path:path}", status_code=204)
async def delete_workspace_file(path: str, request: Request) -> None:
    """Remove a file the agent wrote."""
    user_id = await memory_user_id(request)
    _item, namespace, key = await _find(user_id, path)
    store = await _get_store()
    await store.adelete(namespace, key)
    logger.info("Workspace file %s deleted for %s", key, user_id)
