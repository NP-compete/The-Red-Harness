"""Editing this deployment's configuration from a browser."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from agent.aegra.auth_helpers import check_ldap_role
from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.ui_config_mode import (
    editable_paths,
    editing_allowed_now,
    mode_from,
)
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

STORE = "UI_CONFIG_STORE"

_NO_STORE = (
    "This deployment allows editing, but no store is chosen to keep the "
    "change in, so nothing was changed. Set UI_CONFIG_STORE to 'postgres' to "
    "keep changes, or to 'memory' to keep them for the life of this process."
)

_overlay: InMemoryOverlay | None = None


def overlay_in_use() -> InMemoryOverlay | None:
    """The store edits are going to, if any."""
    return _overlay


def forget_overlay() -> None:
    """Drop the store. For tests, which must not share one."""
    global _overlay  # noqa: PLW0603
    _overlay = None


def _build_postgres_overlay() -> Any:
    """The durable store, connected and ready."""
    from agent.src.agent.config.overlay_postgres import PostgresOverlay
    from agent.src.settings import settings

    made = PostgresOverlay(
        dsn=(
            f"host={settings.POSTGRES_HOST} port={settings.POSTGRES_PORT} "
            f"dbname={settings.POSTGRES_DB} user={settings.POSTGRES_USER} "
            f"password={settings.POSTGRES_PASSWORD}"
        )
    )
    made.ensure_table()
    return made


def _chosen_store() -> str:
    """The store named in the environment, lowercased, or an empty string."""
    return os.environ.get(STORE, "").strip().lower()


def _store() -> Any | None:
    """The chosen store, built once, or `None` if none is chosen."""
    global _overlay  # noqa: PLW0603
    if _overlay is not None:
        return _overlay

    chosen = _chosen_store()
    if chosen == "memory":
        _overlay = InMemoryOverlay()
    elif chosen == "postgres":
        try:
            _overlay = _build_postgres_overlay()
        except Exception as error:
            logger.error("Configuration store unreachable: %s", error)
            raise HTTPException(
                status_code=501,
                detail=(
                    "This deployment keeps configuration edits in a database, "
                    f"and the database could not be reached "
                    f"({type(error).__name__}), so nothing was changed."
                ),
            ) from None

    if _overlay is not None:
        from agent.src.agent.config import resolution

        resolution.use_overlay(_overlay)

    return _overlay


def _is_durable() -> bool:
    """Whether an edit outlives this process."""
    return _chosen_store() == "postgres"


class Edit(BaseModel):
    """Request body replacing the content of one config file."""

    path: str
    content: str
    base_version: int | None = None


class Chosen(BaseModel):
    """Request body naming a single config path."""

    path: str


class Rewind(BaseModel):
    """Request body asking for a config path to go back to a version."""

    path: str
    version: int


def _current_version(overlay: Any | None, path: str) -> int:
    """The version an editor must hand back, or 0 for the baseline."""
    if overlay is None:
        return 0
    kept = overlay.history(path)
    return kept[-1].version if kept else 0


class EditingStateOut(BaseModel):
    """Whether config editing is on, and what backs it."""

    mode: str
    editable: bool
    paths: list[str]
    store: str
    durable: bool


class ConfigTreeFileOut(BaseModel):
    """One file in the config tree and whether it can be edited."""

    path: str
    bytes: int
    editable: bool


class ConfigTreeOut(BaseModel):
    """The config tree, with counts of what is editable and why."""

    root: str
    mode: str
    files: list[ConfigTreeFileOut]
    total: int
    editable: int
    why_not_all: str


class InertSectionOut(BaseModel):
    """A section in this file that this file does not drive."""

    section: str
    decided_by: str


class ConfigFileOut(BaseModel):
    """The content of one config file, with any inert sections flagged."""

    path: str
    content: str
    exists: bool
    version: int
    inert: list[InertSectionOut] = []


class SettingsFieldOut(BaseModel):
    """One settings field, its value, and where that value came from."""

    name: str
    value: Any = None
    default: Any = None
    from_env: bool
    overridden: bool
    masked: bool
    description: str = ""


class SettingsViewOut(BaseModel):
    """Every settings field, with counts by provenance."""

    fields: list[SettingsFieldOut]
    total: int
    from_env: int
    overridden: int
    masked: int
    loosened: list[str] = []
    editable: bool
    why_readonly: str


class ConfigWrittenOut(BaseModel):
    """What every write to the tree answers with."""

    path: str
    version: int
    author: str
    at: str
    durable: bool


class GraphEditOut(BaseModel):
    """A change proposed from the diagram, previewed or written."""

    path: str
    written: bool
    content: str | None = None
    version: int | None = None
    author: str | None = None
    at: str | None = None
    durable: bool | None = None


class AdoptBaselineOut(BaseModel):
    """Dropping an override, including when there was none."""

    path: str
    status: str | None = None
    version: int | None = None
    author: str | None = None
    at: str | None = None
    durable: bool | None = None


class DriftPathOut(BaseModel):
    """One config path that the overlay currently changes."""

    path: str
    baseline: str | None = None
    overlay: str
    version: int
    author: str
    at: str


class DriftOut(BaseModel):
    """Every config path that the overlay currently changes."""

    paths: list[DriftPathOut]


class HistoryVersionOut(BaseModel):
    """One recorded version of a config file."""

    version: int
    author: str
    at: str
    content: str | None = None


class HistoryOut(BaseModel):
    """Every recorded version of one config file."""

    path: str
    versions: list[HistoryVersionOut]


class GraphNodeOut(BaseModel):
    """One box in the diagram (E34)."""

    id: str
    kind: str
    label: str
    path: str
    error: str | None = None
    description: str | None = None
    model: str | None = None
    enabled: bool | None = None
    tier: str | None = None
    routing_enabled: bool | None = None


class GraphEdgeOut(BaseModel):
    """One arrow in the config diagram."""

    from_: str = Field(alias="from")
    to: str
    kind: str
    broken: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class ConfigGraphOut(BaseModel):
    """The config tree as a diagram, with anything broken flagged."""

    root: str
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    problems: list[Any]
    element_types: list[str]
    counts: dict[str, int]


class TarballResponse(Response):
    """Declares the media type the export route actually sends."""

    media_type = "application/gzip"


def _inert_in(path: str, text: str) -> list[dict[str, str]]:
    """Which sections of this text the file does not decide."""
    if not path.endswith("runtime/agent.yaml") or not text.strip():
        return []

    import yaml

    from agent.src.agent.config.validate import AGENT_SECTIONS

    try:
        raw = yaml.safe_load(text) or {}
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []

    return [
        {"section": key, "decided_by": AGENT_SECTIONS[key]}
        for key in sorted(raw)
        if AGENT_SECTIONS.get(key)
    ]


def _is_editable(path: str) -> bool:
    """Whether this deployment considers this path editable."""
    return any(path == one or path.startswith(one) for one in editable_paths() if one)


def _not_editable(path: str) -> HTTPException:
    """The error raised when a path is not one of the editable ones."""
    return HTTPException(
        status_code=400,
        detail=(
            f"{path} is not an editable path. These are: {', '.join(editable_paths())}"
        ),
    )


def _baseline_of(key: str) -> str | None:
    """What the mounted tree says for this path, if anything."""
    from agent.src.agent.config.paths import config_root

    prefix = "config/agent/"
    if not key.startswith(prefix):
        return None
    path = config_root() / key[len(prefix) :]
    try:
        return path.read_text()
    except OSError:
        return None


class GraphEdit(BaseModel):
    """One field on one box (E34-T3)."""

    node_id: str
    field: str
    value: Any
    base_version: int | None = None
    preview: bool = False


def _reading_router() -> APIRouter:
    """What a deployment reports about itself. Always present."""
    router = APIRouter(prefix="/config", tags=["config"])

    @router.get("/editing", responses={200: {"model": EditingStateOut}})
    async def editing_state() -> dict[str, Any]:
        """Whether this deployment may be reconfigured, and of what."""
        chosen = _chosen_store()
        return {
            "mode": mode_from(os.environ.get("UI_CONFIG_MODE")),
            "editable": editing_allowed_now(),
            "paths": list(editable_paths()),
            "store": chosen or "none",
            "durable": _is_durable(),
        }

    @router.get("/file", responses={200: {"model": ConfigFileOut}})
    async def read_file(request: Request, path: str) -> dict[str, Any]:
        """One configuration file, as the agent now reads it."""
        from agent.src.agent.config.paths import config_root
        from agent.src.agent.config.resolution import effective_text

        await check_ldap_role(request, developer_only=True)

        if not _is_editable(path):
            raise _not_editable(path)

        prefix = "config/agent/"
        on_disk = (
            config_root() / path[len(prefix) :] if path.startswith(prefix) else None
        )

        overlay = _store()
        version = _current_version(overlay, path)
        edited = overlay.current(path) if overlay is not None else None
        if edited is not None:
            return {
                "path": path,
                "content": edited,
                "exists": True,
                "version": version,
                "inert": _inert_in(path, edited),
            }

        if on_disk is None or not on_disk.is_file():
            return {
                "path": path,
                "content": "",
                "exists": False,
                "version": version,
                "inert": [],
            }

        text = effective_text(on_disk)
        return {
            "path": path,
            "content": text,
            "exists": True,
            "version": version,
            "inert": _inert_in(path, text),
        }

    @router.get("/tree", responses={200: {"model": ConfigTreeOut}})
    async def tree(request: Request) -> dict[str, Any]:
        """Every file in the config tree, and which may be edited."""
        from agent.src.agent.config.paths import config_root

        await check_ldap_role(request, developer_only=True)

        root = config_root()
        prefix = "config/agent/"
        files: list[dict[str, Any]] = []
        if root.is_dir():
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.name.endswith(".bak"):
                    continue
                relative = f"{prefix}{path.relative_to(root).as_posix()}"
                files.append(
                    {
                        "path": relative,
                        "bytes": path.stat().st_size,
                        "editable": _is_editable(relative),
                    }
                )

        editable = sum(1 for f in files if f["editable"])
        return {
            "root": str(root),
            "mode": mode_from(os.environ.get("UI_CONFIG_MODE")),
            "files": files,
            "total": len(files),
            "editable": editable,
            "why_not_all": (
                f"{len(files) - editable} of {len(files)} files are visible but "
                "not editable from here. The editable set is fixed by the "
                "deployment; widen it with UI_CONFIG_EDITABLE_EXTRA."
            ),
        }

    @router.get("/graph", responses={200: {"model": ConfigGraphOut}})
    async def config_graph(request: Request) -> dict[str, Any]:
        """The configuration as a picture, derived on every request (E34)."""
        await check_ldap_role(request, developer_only=True)

        from agent.src.config_surface.graph_model import build_graph

        return build_graph()

    @router.get("/settings", responses={200: {"model": SettingsViewOut}})
    async def settings_fields(request: Request) -> dict[str, Any]:
        """The configuration that lives in the environment, not a file."""
        from agent.src.agent.config.settings_view import settings_view

        await check_ldap_role(request, developer_only=True)
        return settings_view()

    @router.get("/drift", responses={200: {"model": DriftOut}})
    async def drift(request: Request) -> dict[str, Any]:
        """Every path this deployment has overridden, and against what."""
        await check_ldap_role(request, developer_only=True)

        overlay = _store()
        if overlay is None:
            return {"paths": []}

        found = []
        for key in overlay.overridden():
            latest = overlay.history(key)[-1]
            baseline = _baseline_of(key)
            if latest.content == baseline:
                continue
            found.append(
                {
                    "path": key,
                    "baseline": baseline,
                    "overlay": latest.content,
                    "version": latest.version,
                    "author": latest.author,
                    "at": latest.at,
                }
            )
        return {"paths": found}

    @router.get("/history", responses={200: {"model": HistoryOut}})
    async def history(request: Request, path: str) -> dict[str, Any]:
        """Every version of one path, oldest first."""
        await check_ldap_role(request, developer_only=True)

        overlay = _store()
        versions = overlay.history(path) if overlay is not None else []
        return {
            "path": path,
            "versions": [
                {
                    "version": one.version,
                    "author": one.author,
                    "at": one.at,
                    "content": one.content,
                }
                for one in versions
            ],
        }

    @router.get(
        "/export",
        response_class=TarballResponse,
        responses={
            200: {
                "content": {
                    "application/gzip": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
                "description": "The effective configuration tree as a gzipped tar.",
            }
        },
    )
    async def export_configuration(request: Request) -> Any:
        """The whole effective tree, as an archive to commit."""
        import io
        import tarfile
        import time

        from fastapi.responses import Response

        from agent.src.agent.config.export import effective_tree

        await check_ldap_role(request, developer_only=True)

        held = effective_tree()
        buffer = io.BytesIO()
        now = int(time.time())
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, content in sorted(held.items()):
                raw = content.encode("utf-8")
                entry = tarfile.TarInfo(name=name)
                entry.size = len(raw)
                entry.mtime = now
                entry.mode = 0o644
                archive.addfile(entry, io.BytesIO(raw))

        return Response(
            content=buffer.getvalue(),
            media_type="application/gzip",
            headers={"Content-Disposition": 'attachment; filename="config.tar.gz"'},
        )

    return router


async def _apply_edit(
    *, path: str, content: str, base_version: int | None, author: str
) -> dict[str, Any]:
    """Record one edit, with every check the write surface has."""
    if not _is_editable(path):
        raise _not_editable(path)

    overlay = _store()
    if overlay is None:
        raise HTTPException(
            status_code=501,
            detail=(
                "This deployment allows editing, but no store is chosen "
                f"to keep the edit in, so nothing was changed. Set {STORE} "
                "to 'postgres' to keep edits across restarts, or to "
                "'memory' to keep them for the life of this process."
            ),
        )

    if base_version is not None:
        live = _current_version(overlay, path)
        if live != base_version:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{path} changed since you opened it: you have "
                    f"version {base_version}, it is now {live}. "
                    "Reload it, reapply your change, and save again."
                ),
            )
    else:
        logger.warning(
            "Configuration overwritten without a version check: %s by %s",
            path,
            author,
        )

    from agent.src.agent.config.editing import EditRefused, apply_all

    try:
        written = apply_all(overlay, {path: content}, author=author)[0]
    except EditRefused as refused:
        raise HTTPException(
            status_code=422,
            detail=f"That edit would make the configuration invalid: {refused}",
        ) from None
    logger.warning(
        "Configuration edited: %s version %d by %s",
        written.path,
        written.version,
        written.author,
    )
    return {
        "path": written.path,
        "version": written.version,
        "author": written.author,
        "at": written.at,
        "durable": _is_durable(),
    }


def _writing_router() -> APIRouter:
    """The write surface. Built only where it is wanted."""
    router = APIRouter(prefix="/config", tags=["config"])

    @router.put("/edit", responses={200: {"model": ConfigWrittenOut}})
    async def edit_configuration(request: Request, body: Edit) -> dict[str, Any]:
        """Record an edit to one configuration path."""
        author = await check_ldap_role(request, developer_only=True)
        return await _apply_edit(
            path=body.path,
            content=body.content,
            base_version=body.base_version,
            author=author,
        )

    @router.post("/graph/edit", responses={200: {"model": GraphEditOut}})
    async def edit_from_graph(request: Request, body: GraphEdit) -> dict[str, Any]:
        """Change one field on one box in the diagram (E34-T3)."""
        author = await check_ldap_role(request, developer_only=True)

        from agent.src.agent.config.paths import config_root
        from agent.src.config_surface.graph_edit import (
            GraphEditRefused,
            propose,
        )

        try:
            path, text = propose(
                node_id=body.node_id,
                field=body.field,
                value=body.value,
                root=config_root(),
            )
        except GraphEditRefused as refused:
            raise HTTPException(status_code=422, detail=str(refused)) from None

        if body.preview:
            return {"path": path, "content": text, "written": False}

        written = await _apply_edit(
            path=path, content=text, base_version=body.base_version, author=author
        )
        return {**written, "written": True}

    @router.post("/adopt-baseline", responses={200: {"model": AdoptBaselineOut}})
    async def adopt_baseline(request: Request, body: Chosen) -> dict[str, Any]:
        """Stop overriding this path, whatever the repository now says."""
        author = await check_ldap_role(request, developer_only=True)
        overlay = _store()
        if overlay is None:
            raise HTTPException(status_code=501, detail=_NO_STORE)

        if body.path not in overlay.overridden():
            return {"path": body.path, "status": "not overridden"}

        written = overlay.adopt_baseline(body.path, author=author)
        logger.warning(
            "Configuration override dropped: %s by %s", written.path, written.author
        )
        return {
            "path": written.path,
            "version": written.version,
            "author": written.author,
            "at": written.at,
            "durable": _is_durable(),
        }

    @router.post("/revert", responses={200: {"model": ConfigWrittenOut}})
    async def revert(request: Request, body: Rewind) -> dict[str, Any]:
        """Go back to a version this deployment chose earlier."""
        from agent.src.agent.config.overlay import NothingToRevertTo

        author = await check_ldap_role(request, developer_only=True)
        overlay = _store()
        if overlay is None:
            raise HTTPException(status_code=501, detail=_NO_STORE)

        try:
            written = overlay.revert(body.path, to=body.version, author=author)
        except NothingToRevertTo:
            raise HTTPException(
                status_code=404,
                detail=f"{body.path} has no version {body.version} to go back to",
            ) from None

        logger.warning(
            "Configuration reverted: %s to the content of version %d by %s",
            body.path,
            body.version,
            author,
        )
        return {
            "path": written.path,
            "version": written.version,
            "author": written.author,
            "at": written.at,
            "durable": _is_durable(),
        }

    return router


def register(app: Any) -> None:
    """Mount the reading surface, and the writing one only if allowed."""
    app.include_router(_reading_router())
    if editing_allowed_now():
        logger.warning(
            "Configuration editing is enabled: this deployment accepts "
            "configuration writes from the browser"
        )
        app.include_router(_writing_router())
        _install_overlay_now()


def _install_overlay_now() -> None:
    """Put the overlay in front of config reads before anything reads."""
    try:
        _store()
    except Exception as error:  # noqa: BLE001 - startup must not fail here
        logger.error(
            "Configuration overlay not installed at startup (%s): edits already "
            "stored will not be read until this succeeds",
            type(error).__name__,
        )
