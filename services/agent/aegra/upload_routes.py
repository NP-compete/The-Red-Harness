"""Archive and file ingestion into the agent's data directory."""

from __future__ import annotations

import asyncio
import os
import shutil
import stat
import tarfile
import tempfile
import time
import uuid
import zipfile
import zlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path, PurePosixPath
from typing import IO, Literal, TypeAlias
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from starlette.datastructures import UploadFile

from agent.aegra.auth_helpers import check_ldap_role
from agent.src.audit.context import bind_audit_context
from agent.src.audit.emitter import emit_audit_event
from agent.src.audit.events import AuditEventType
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

upload_router = APIRouter(tags=["upload"])

LIVE_DIR = "current"

_STAGING_PREFIX = ".staging-"
_OLD_PREFIX = ".old-"
_LOCK_NAME = ".upload.lock"

_ARCHIVE_ERRORS = (
    zipfile.BadZipFile,
    zipfile.LargeZipFile,
    tarfile.TarError,
    zlib.error,
    EOFError,
    ValueError,
    RuntimeError,
    NotImplementedError,
)

_CONTROL_CHARS = frozenset(chr(c) for c in range(32)) | {chr(127)}

_MAX_NAME_COMPONENT = 255

_DIR_MODE = 0o775
_FILE_MODE = 0o664

_CHUNK = 64 * 1024

_TAR_MAGIC_OFFSET = 257
_TAR_MAGIC_END = 262

Mode: TypeAlias = Literal["replace", "merge"]


class UploadRejected(Exception):
    """A payload failed validation. Surfaces as a 400 with the given reason."""


class UploadResponse(BaseModel):
    """Result of a successful upload."""

    mode: Mode
    files_written: int
    files_skipped: int
    bytes_written: int


class DeleteResponse(BaseModel):
    """Result of clearing the data directory."""

    files_deleted: int
    bytes_deleted: int


@dataclass
class _Entry:
    """One payload item, normalized across zip entries, tar members and files."""

    name: str
    is_dir: bool
    is_regular: bool
    open: Callable[[], IO[bytes]]


def _chmod_shared(path: Path, mode: int) -> None:
    """Make a path group-writable, ignoring failure."""
    try:
        path.chmod(mode)
    except OSError as exc:  # pragma: no cover - filesystem dependent
        logger.debug("upload_chmod_skipped", path=str(path), error=str(exc))


def _mkdir_shared(path: Path) -> None:
    """Create a directory (and parents) group-writable."""
    path.mkdir(parents=True, exist_ok=True)
    _chmod_shared(path, _DIR_MODE)


def _link_or_copy(src: str, dst: str, *, follow_symlinks: bool = True) -> None:
    """Hardlink a file into staging, falling back to a real copy."""
    try:
        os.link(src, dst)
    except OSError as exc:  # pragma: no cover - requires a foreign-owned tree
        logger.warning("upload_hardlink_fallback_copy", error=str(exc))
        shutil.copy2(src, dst)


def _allowed_extensions() -> frozenset[str]:
    """Parse UPLOAD_ALLOWED_EXTENSIONS into a lowercase set of suffixes."""
    return frozenset(
        ext.strip().lower()
        for ext in settings.UPLOAD_ALLOWED_EXTENSIONS.split(",")
        if ext.strip()
    )


def _require_enabled() -> None:
    """Raise 404 if the upload feature is disabled."""
    if not settings.UPLOAD_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload feature is disabled"
        )


def _data_root() -> Path:
    """Return the writable data mount, creating it if absent."""
    from agent.src.data_paths import data_dir

    root = data_dir()
    _mkdir_shared(root)
    return root


def _zip_entries(archive: zipfile.ZipFile) -> Iterator[_Entry]:
    """Yield normalized entries from a zip archive."""
    for info in archive.infolist():
        mode = info.external_attr >> 16
        is_dir = info.is_dir()
        yield _Entry(
            name=info.filename,
            is_dir=is_dir,
            is_regular=not is_dir and not stat.S_ISLNK(mode),
            open=partial(archive.open, info),
        )


def _tar_entries(archive: tarfile.TarFile) -> Iterator[_Entry]:
    """Yield normalized entries from a tar archive."""

    def _open(member: tarfile.TarInfo) -> IO[bytes]:
        fh = archive.extractfile(member)
        if fh is None:  # pragma: no cover - non-regular members are skipped
            raise UploadRejected(f"unreadable archive member: {member.name}")
        return fh

    for member in archive:
        yield _Entry(
            name=member.name,
            is_dir=member.isdir(),
            is_regular=member.isreg(),
            open=partial(_open, member),
        )


def _loose_entries(files: list[UploadFile]) -> Iterator[_Entry]:
    """Yield normalized entries from directly posted files."""

    def _open(upload: UploadFile) -> IO[bytes]:
        stream: IO[bytes] = upload.file
        return stream

    for upload in files:
        yield _Entry(
            name=upload.filename or "",
            is_dir=False,
            is_regular=True,
            open=partial(_open, upload),
        )


def _safe_destination(name: str, root: Path) -> Path:
    """Resolve an entry name inside root, rejecting traversal attempts."""
    if not name or name.endswith("/"):
        raise UploadRejected("entry has no filename")

    decoded = unquote(name)

    if any(ch in decoded for ch in _CONTROL_CHARS):
        raise UploadRejected("filename contains control characters")

    if "\\" in decoded:
        raise UploadRejected(f"backslash in path rejected: {name}")

    if decoded != name:
        d = PurePosixPath(decoded)
        if d.is_absolute() or ".." in d.parts:
            raise UploadRejected(f"percent-encoded path rejected: {name}")

    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        raise UploadRejected(f"path traversal rejected: {name}")

    for part in pure.parts:
        if len(part.encode()) > _MAX_NAME_COMPONENT:
            raise UploadRejected(
                f"path component exceeds {_MAX_NAME_COMPONENT} bytes: {part[:40]}…"
            )

    destination = (root / pure).resolve()
    if not destination.is_relative_to(root.resolve()):
        raise UploadRejected(f"path traversal rejected: {name}")
    return destination


def _write_entry(source: IO[bytes], destination: Path) -> int:
    """Stream one entry to disk, enforcing the per-file cap as it goes."""
    _mkdir_shared(destination.parent)
    written = 0
    destination.unlink(missing_ok=True)
    with destination.open("wb") as out:
        while chunk := source.read(_CHUNK):
            written += len(chunk)
            if written > settings.UPLOAD_MAX_FILE_BYTES:
                raise UploadRejected(
                    f"file exceeds per-file cap of "
                    f"{settings.UPLOAD_MAX_FILE_BYTES} bytes: {destination.name}"
                )
            out.write(chunk)
    _chmod_shared(destination, _FILE_MODE)
    return written


def _tree_size(root: Path) -> int:
    """Return the total size in bytes of all files under root."""
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def _populate(
    entries: Iterator[_Entry],
    staging: Path,
    baseline: int,
    *,
    apply_allowlist: bool,
) -> tuple[int, int, int]:
    """Write permitted entries into staging, enforcing every per-entry guard."""
    allowed = _allowed_extensions() if apply_allowlist else frozenset()
    written_files = skipped = 0
    written_bytes = 0
    seen = 0
    tree_bytes = baseline

    for entry in entries:
        seen += 1
        if seen > settings.UPLOAD_MAX_FILE_COUNT:
            raise UploadRejected(
                f"upload exceeds {settings.UPLOAD_MAX_FILE_COUNT} entries"
            )

        if entry.is_dir:
            continue

        if not entry.is_regular:
            skipped += 1
            continue

        destination = _safe_destination(entry.name, staging)

        if apply_allowlist and PurePosixPath(entry.name).suffix.lower() not in allowed:
            skipped += 1
            continue

        replaced = destination.stat().st_size if destination.is_file() else 0

        with entry.open() as source:
            size = _write_entry(source, destination)

        written_files += 1
        written_bytes += size
        tree_bytes += size - replaced
        if tree_bytes > settings.UPLOAD_MAX_EXTRACTED_BYTES:
            raise UploadRejected(
                f"total size exceeds {settings.UPLOAD_MAX_EXTRACTED_BYTES} bytes"
            )

    if written_files == 0:
        raise UploadRejected("payload contained no permitted files")

    return written_files, skipped, written_bytes


def _publish(staging: Path, live: Path) -> None:
    """Swap staging into place as the live tree."""
    old = live.parent / f"{_OLD_PREFIX}{uuid.uuid4().hex}"
    moved = False
    if live.exists():
        os.rename(live, old)
        moved = True
    try:
        os.rename(staging, live)
    except OSError:
        if moved:
            os.rename(old, live)
        raise
    if moved:
        shutil.rmtree(old, ignore_errors=True)


class UploadBusy(Exception):
    """Another upload holds the lock. Surfaces as a 409."""


def _sweep_orphans(data_root: Path) -> None:
    """Delete staging/old directories abandoned by a crashed or raced upload."""
    for path in data_root.iterdir():
        if path.name.startswith((_STAGING_PREFIX, _OLD_PREFIX)) and path.is_dir():
            logger.warning("upload_orphan_swept", path=path.name)
            shutil.rmtree(path, ignore_errors=True)


@contextmanager
def _upload_lock(data_root: Path) -> Iterator[None]:
    """Serialize uploads across every process sharing the data volume."""
    lock = data_root / _LOCK_NAME
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        try:
            stale_stat = lock.stat()
        except FileNotFoundError:
            raise UploadBusy("another upload is in progress") from None
        age = time.time() - stale_stat.st_mtime
        if age < settings.UPLOAD_LOCK_TIMEOUT_SECONDS:
            raise UploadBusy("another upload is in progress") from None

        stolen = data_root / f"{_LOCK_NAME}.stale-{uuid.uuid4().hex}"
        try:
            os.rename(lock, stolen)
        except OSError:
            raise UploadBusy("another upload is in progress") from None

        try:
            stolen_ino = os.stat(stolen).st_ino
        except OSError:
            raise UploadBusy("another upload is in progress") from None

        if stolen_ino != stale_stat.st_ino:
            try:
                os.link(stolen, lock)
            except OSError:
                logger.warning("upload_lock_restore_skipped", lock=str(lock))
            Path(stolen).unlink(missing_ok=True)
            raise UploadBusy("another upload is in progress") from None

        logger.warning("upload_lock_stale_broken", age_seconds=int(age))
        Path(stolen).unlink(missing_ok=True)
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            raise UploadBusy("another upload is in progress") from None

    our_token = uuid.uuid4().hex
    try:
        os.write(fd, f"{our_token}\n{os.getpid()}\n".encode())
    finally:
        os.close(fd)

    try:
        yield
    finally:
        held_by: str | None
        try:
            held_by = lock.read_text().split("\n", 1)[0]
        except OSError:
            held_by = None
        if held_by == our_token:
            lock.unlink(missing_ok=True)
        elif held_by is not None:
            logger.warning("upload_lock_not_ours_on_release", held_by=held_by)


def _ingest(
    payload: Path | list[UploadFile], mode: Mode, data_root: Path
) -> UploadResponse:
    """Stage, validate and publish a payload. Runs in a worker thread."""
    live = data_root / LIVE_DIR
    staging = data_root / f"{_STAGING_PREFIX}{uuid.uuid4().hex}"

    with _upload_lock(data_root):
        try:
            _sweep_orphans(data_root)
            if mode == "merge" and live.is_dir():
                shutil.copytree(live, staging, copy_function=_link_or_copy)
                baseline = _tree_size(staging)
            else:
                _mkdir_shared(staging)
                baseline = 0

            try:
                if isinstance(payload, list):
                    written, skipped, written_bytes = _populate(
                        _loose_entries(payload),
                        staging,
                        baseline,
                        apply_allowlist=True,
                    )
                elif zipfile.is_zipfile(payload):
                    with zipfile.ZipFile(payload) as archive:
                        written, skipped, written_bytes = _populate(
                            _zip_entries(archive),
                            staging,
                            baseline,
                            apply_allowlist=False,
                        )
                else:
                    with tarfile.open(payload) as archive:
                        written, skipped, written_bytes = _populate(
                            _tar_entries(archive),
                            staging,
                            baseline,
                            apply_allowlist=False,
                        )
            except _ARCHIVE_ERRORS as exc:
                raise UploadRejected(
                    f"archive could not be read: {type(exc).__name__}"
                ) from exc

            _publish(staging, live)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    return UploadResponse(
        mode=mode,
        files_written=written,
        files_skipped=skipped,
        bytes_written=written_bytes,
    )


def _clear(data_root: Path) -> DeleteResponse:
    """Remove the live tree. Runs in a worker thread."""
    live = data_root / LIVE_DIR

    with _upload_lock(data_root):
        _sweep_orphans(data_root)
        if not live.is_dir():
            return DeleteResponse(files_deleted=0, bytes_deleted=0)

        files = [p for p in live.rglob("*") if p.is_file()]
        count = len(files)
        size = sum(p.stat().st_size for p in files)

        condemned = data_root / f"{_OLD_PREFIX}{uuid.uuid4().hex}"
        os.rename(live, condemned)
        shutil.rmtree(condemned, ignore_errors=True)

    return DeleteResponse(files_deleted=count, bytes_deleted=size)


def _sniff_archive(path: Path) -> bool:
    """Return whether a buffered payload is a readable zip or tar."""
    try:
        if zipfile.is_zipfile(path):
            return True
    except _ARCHIVE_ERRORS as exc:
        raise UploadRejected(
            f"archive could not be read: {type(exc).__name__}"
        ) from exc

    try:
        return tarfile.is_tarfile(path)
    except _ARCHIVE_ERRORS as exc:
        raise UploadRejected(
            f"archive could not be read: {type(exc).__name__}"
        ) from exc


async def _looks_like_archive(upload: UploadFile) -> bool:
    """Detect a zip/tar by magic bytes without consuming the stream."""
    head: bytes = await upload.read(_TAR_MAGIC_END)
    await upload.seek(0)
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return True
    if head.startswith((b"\x1f\x8b", b"BZh", b"\xfd7zXZ")):
        return True
    return head[_TAR_MAGIC_OFFSET:_TAR_MAGIC_END] == b"ustar"


async def _buffer(upload: UploadFile, destination: Path) -> None:
    """Stream an upload to disk, enforcing the archive size cap."""
    total = 0
    with destination.open("wb") as out:
        while chunk := await upload.read(_CHUNK):
            total += len(chunk)
            if total > settings.UPLOAD_MAX_ARCHIVE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"Upload exceeds maximum size of "
                        f"{settings.UPLOAD_MAX_ARCHIVE_BYTES} bytes"
                    ),
                )
            out.write(chunk)
    await upload.seek(0)


_UPLOAD_REQUEST_BODY_SCHEMA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string", "format": "binary"},
                            "description": (
                                "One .zip/.tar archive, which replaces the "
                                "whole tree, or one or more loose files, "
                                "which are merged into it."
                            ),
                        }
                    },
                    "required": ["files"],
                }
            }
        },
    }
}


@upload_router.post(
    "/upload",
    response_model=UploadResponse,
    openapi_extra=_UPLOAD_REQUEST_BODY_SCHEMA,
)
async def upload(request: Request) -> UploadResponse:
    """Publish an archive or a set of files to the agent's data directory."""
    _require_enabled()
    user_id = await check_ldap_role(request, developer_only=True)
    bind_audit_context(user=user_id)

    data_root = _data_root()
    scratch = Path(tempfile.mkdtemp(prefix="upload-"))
    try:
        try:
            async with request.form(
                max_files=settings.UPLOAD_MAX_FILE_COUNT,
                max_fields=settings.UPLOAD_MAX_FILE_COUNT,
            ) as form:
                files = [f for f in form.getlist("files") if isinstance(f, UploadFile)]
                return await _handle_upload(files, data_root, scratch, user_id)
        except HTTPException:
            raise
        except (ValueError, AssertionError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Malformed multipart body: {exc}"
            ) from None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


async def _handle_upload(
    files: list[UploadFile], data_root: Path, scratch: Path, user_id: str
) -> UploadResponse:
    """Validate the parsed parts and publish them. Body is already read."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    payload: Path | list[UploadFile]
    mode: Mode
    if len(files) == 1:
        buffered = scratch / "payload"
        await _buffer(files[0], buffered)
        try:
            is_archive = _sniff_archive(buffered)
        except UploadRejected as exc:
            logger.warning("upload_rejected", user_id=user_id, reason=str(exc))
            emit_audit_event(
                AuditEventType.DATA_UPLOAD_REJECTED,
                user=user_id,
                mode="unknown",
                reason=str(exc),
            )
            raise HTTPException(status_code=400, detail=str(exc)) from None
        if is_archive:
            payload, mode = buffered, "replace"
        else:
            name = (files[0].filename or "").lower()
            if name.endswith((".zip", ".tar")):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "File is named as an archive but is not a valid zip or tar"
                    ),
                )
            payload, mode = files, "merge"
    else:
        for candidate in files:
            if await _looks_like_archive(candidate):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Archive '{candidate.filename}' must be uploaded on "
                        f"its own, not alongside other files"
                    ),
                )
        payload, mode = files, "merge"

    try:
        result = await asyncio.to_thread(_ingest, payload, mode, data_root)
    except UploadRejected as exc:
        logger.warning("upload_rejected", user_id=user_id, reason=str(exc))
        emit_audit_event(
            AuditEventType.DATA_UPLOAD_REJECTED,
            user=user_id,
            mode=mode,
            reason=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except UploadBusy as exc:
        logger.info("upload_busy", user_id=user_id)
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except OSError as exc:
        logger.exception("upload_publish_failed", user_id=user_id, error=str(exc))
        raise HTTPException(
            status_code=500, detail="Failed to publish upload"
        ) from None

    logger.info(
        "upload_published",
        user_id=user_id,
        mode=result.mode,
        files_written=result.files_written,
        files_skipped=result.files_skipped,
        bytes_written=result.bytes_written,
    )
    emit_audit_event(
        AuditEventType.DATA_UPLOAD,
        user=user_id,
        mode=result.mode,
        files_written=result.files_written,
        files_skipped=result.files_skipped,
        bytes_written=result.bytes_written,
    )
    return result


@upload_router.delete("/upload", response_model=DeleteResponse)
async def clear_uploaded_data(request: Request) -> DeleteResponse:
    """Delete everything previously published to the agent's data directory."""
    _require_enabled()
    user_id = await check_ldap_role(request, developer_only=True)
    bind_audit_context(user=user_id)

    data_root = _data_root()
    try:
        result = await asyncio.to_thread(_clear, data_root)
    except UploadBusy as exc:
        logger.info("upload_busy", user_id=user_id)
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except OSError as exc:
        logger.exception("upload_clear_failed", user_id=user_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to clear data") from None

    logger.warning(
        "upload_data_cleared",
        user_id=user_id,
        files_deleted=result.files_deleted,
        bytes_deleted=result.bytes_deleted,
    )
    emit_audit_event(
        AuditEventType.DATA_DELETE,
        user=user_id,
        files_deleted=result.files_deleted,
        bytes_deleted=result.bytes_deleted,
    )
    return result
