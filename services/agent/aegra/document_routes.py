"""Documents on a mounted volume."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi import File as FileParam
from pydantic import BaseModel

from agent.aegra.auth_helpers import authenticated_user_id
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(prefix=settings.DOCUMENTS_ROUTE_PREFIX, tags=["documents"])


class UsageOut(BaseModel):
    """How full the volume is."""

    used_bytes: int
    capacity_bytes: int
    percent_used: float
    warning: bool


class DocumentOut(BaseModel):
    """One document in the agent's library."""

    path: str
    bytes: int
    modified: float


class DocumentListOut(BaseModel):
    """Files on the volume, and how full it is."""

    documents: list[DocumentOut]
    usage: UsageOut


class DocumentUploadedOut(BaseModel):
    """What an upload stored, and what is left of the quota."""

    uploaded: list[Any]
    usage: UsageOut


class DocumentContentOut(BaseModel):
    """One file's content, for viewing or editing."""

    path: str
    bytes: int
    content: str
    truncated: bool
    editable: bool


class DocumentWrittenOut(BaseModel):
    """What a write stored, and what is left of the quota."""

    path: str
    bytes: int
    usage: UsageOut


class DocumentDeletedOut(BaseModel):
    """Which document went, and what is left of the quota."""

    deleted: str
    usage: UsageOut


_DEFAULT_CAPACITY_BYTES = settings.DOCUMENTS_CAPACITY_BYTES

_WARN_AT = settings.DOCUMENTS_CAPACITY_WARN_FRACTION

_READABLE_SUFFIXES = {
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".parquet",
    ".xlsx",
    ".txt",
    ".md",
}


def _root() -> Path:
    from agent.src.data_paths import documents_dir

    return documents_dir()


def _capacity_bytes() -> int:
    raw = os.environ.get("DOCUMENTS_MAX_BYTES")
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid DOCUMENTS_MAX_BYTES %r — using default", raw)
    return _DEFAULT_CAPACITY_BYTES


def _used_bytes(root: Path) -> int:
    """Bytes currently on the volume."""
    total = 0
    if not root.is_dir():
        return 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def _usage(root: Path) -> dict[str, Any]:
    used = _used_bytes(root)
    capacity = _capacity_bytes()
    fraction = used / capacity if capacity else 0.0
    return {
        "used_bytes": used,
        "capacity_bytes": capacity,
        "percent_used": round(fraction * 100, 1),
        "warning": fraction >= _WARN_AT,
    }


def _safe_target(root: Path, filename: str) -> Path:
    """Resolve *filename* under *root*, refusing anything that escapes."""
    candidate = (root / filename).resolve()
    if not candidate.is_relative_to(root.resolve()) or candidate == root.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")
    return candidate


@router.get("", responses={200: {"model": DocumentListOut}})
async def list_documents(request: Request) -> dict[str, Any]:
    """Files on the volume, and how full it is."""
    await authenticated_user_id(request, reject_anonymous=True, developer_only=True)
    root = _root()
    files: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            files.append(
                {
                    "path": str(path.relative_to(root)),
                    "bytes": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    return {"documents": files, "usage": _usage(root)}


@router.post("", responses={200: {"model": DocumentUploadedOut}})
async def upload_document(
    request: Request,
    files: list[UploadFile] = FileParam(...),
) -> dict[str, Any]:
    """Add files to the volume, refusing anything that would overfill it."""
    await authenticated_user_id(request, reject_anonymous=True, developer_only=True)
    root = _root()
    root.mkdir(parents=True, exist_ok=True)

    usage = _usage(root)
    remaining = usage["capacity_bytes"] - usage["used_bytes"]

    declared = sum(f.size or 0 for f in files)
    if declared > remaining:
        raise HTTPException(
            status_code=507,
            detail=(
                f"Not enough space: {_mb(declared)} requested, "
                f"{_mb(remaining)} free of {_mb(usage['capacity_bytes'])}. "
                "Delete a document first."
            ),
        )

    written: list[dict[str, Any]] = []
    budget = remaining
    for upload in files:
        target = _safe_target(root, upload.filename or "unnamed")
        if target.suffix.lower() not in _READABLE_SUFFIXES:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"{target.name}: unsupported type. Allowed: "
                    + ", ".join(sorted(_READABLE_SUFFIXES))
                ),
            )

        staging = target.with_name(f".{target.name}.{os.getpid()}.{uuid4().hex}.part")
        size = 0
        try:
            with staging.open("wb") as sink:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > budget:
                        sink.close()
                        staging.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=507,
                            detail=(
                                f"{target.name} exceeds the remaining "
                                f"{_mb(budget)} on the documents volume."
                            ),
                        )
                    sink.write(chunk)
        except HTTPException:
            staging.unlink(missing_ok=True)
            raise
        except OSError as exc:
            staging.unlink(missing_ok=True)
            logger.error("Could not write dataset %s: %s", target, exc)
            raise HTTPException(
                status_code=500, detail=f"Could not write {target.name}"
            ) from exc

        staging.replace(target)
        budget -= size
        written.append({"path": target.name, "bytes": size})

    return {"uploaded": written, "usage": _usage(root)}


class DocumentBody(BaseModel):
    """Text content for a created or replaced document file."""

    content: str


_MAX_EDITABLE_BYTES = settings.DOCUMENTS_MAX_EDITABLE_BYTES


@router.get("/{name:path}", responses={200: {"model": DocumentContentOut}})
async def read_document(name: str, request: Request) -> dict[str, Any]:
    """One file's content, for viewing or editing."""
    await authenticated_user_id(request, reject_anonymous=True, developer_only=True)
    root = _root()
    target = _resolve_existing(root, name)
    if target.is_dir():
        raise HTTPException(status_code=400, detail=f"{name} is a directory")

    with target.open("rb") as handle:
        raw = handle.read(_MAX_EDITABLE_BYTES + 1)
    truncated = len(raw) > _MAX_EDITABLE_BYTES
    return {
        "path": name,
        "bytes": target.stat().st_size,
        "content": raw[:_MAX_EDITABLE_BYTES].decode("utf-8", errors="replace"),
        "truncated": truncated,
        "editable": not truncated,
    }


@router.put("/{name:path}", responses={200: {"model": DocumentWrittenOut}})
async def write_document(
    name: str, body: DocumentBody, request: Request
) -> dict[str, Any]:
    """Create or replace a text document file."""
    await authenticated_user_id(request, reject_anonymous=True, developer_only=True)
    root = _root()
    root.mkdir(parents=True, exist_ok=True)
    target = _safe_target(root, name)
    if target.suffix.lower() not in _READABLE_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"{target.name}: unsupported type. Allowed: "
                + ", ".join(sorted(_READABLE_SUFFIXES))
            ),
        )

    incoming = body.content.encode("utf-8")
    usage = _usage(root)
    existing = target.stat().st_size if target.is_file() else 0
    remaining = usage["capacity_bytes"] - usage["used_bytes"] + existing
    if len(incoming) > remaining:
        raise HTTPException(
            status_code=507,
            detail=(
                f"Not enough space: {_mb(len(incoming))} needed, "
                f"{_mb(remaining)} available."
            ),
        )

    await asyncio.to_thread(target.write_bytes, incoming)
    return {"path": target.name, "bytes": len(incoming), "usage": _usage(root)}


def _resolve_existing(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or not target.exists():
        raise HTTPException(status_code=404, detail=f"No such document: {name}")
    if target == root.resolve():
        raise HTTPException(status_code=400, detail="Refusing to act on the root")
    return target


@router.delete("/{name:path}", responses={200: {"model": DocumentDeletedOut}})
async def delete_document(name: str, request: Request) -> dict[str, Any]:
    """Remove one document file or directory."""
    await authenticated_user_id(request, reject_anonymous=True, developer_only=True)
    root = _root()
    target = _resolve_existing(root, name)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"deleted": name, "usage": _usage(root)}


def _mb(value: int) -> str:
    return f"{value / (1024 * 1024):.1f} MB"
