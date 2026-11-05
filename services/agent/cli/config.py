"""The configuration tree, from a terminal (E28, CFG-10)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ConfigFailed(RuntimeError):
    """The agent would not, or could not, do it."""


class ReadOnlyDeployment(ConfigFailed):
    """This deployment does not accept configuration writes."""


class Transport(Protocol):
    """Makes requests to the agent on the CLI's behalf."""

    def get(self, path: str) -> tuple[int, Any]:
        """GET `path` and return the status and decoded body."""
        ...

    def put(self, path: str, body: dict | None = None) -> tuple[int, Any]:
        """PUT `body` to `path` and return the status and decoded body."""
        ...


@dataclass(frozen=True)
class ConfigFile:
    """One file in the agent's config tree."""

    path: str
    editable: bool
    bytes: int


@dataclass(frozen=True)
class FileText:
    """The content of one config file, at a version."""

    path: str
    content: str
    version: int
    exists: bool


def list_files(*, transport: Transport) -> list[ConfigFile]:
    """Every file in the configuration root, and whether it may be changed."""
    status, payload = transport.get("/config/tree")
    if status != 200:
        raise ConfigFailed(
            f"Could not list the configuration ({status}): {_why(payload)}"
        )
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, list):
        raise ConfigFailed("The agent answered with something that is not a file list")
    return [
        ConfigFile(
            path=str(one.get("path", "")),
            editable=bool(one.get("editable")),
            bytes=int(one.get("bytes") or 0),
        )
        for one in files
        if isinstance(one, dict)
    ]


def show_file(path: str, *, transport: Transport) -> FileText:
    """One file as the agent currently reads it, edits included."""
    from urllib.parse import quote

    status, payload = transport.get(f"/config/file?path={quote(path, safe='')}")
    if status == 404:
        raise ConfigFailed(f"{path} is not a file this deployment will serve")
    if status != 200 or not isinstance(payload, dict):
        raise ConfigFailed(f"Could not read {path} ({status}): {_why(payload)}")
    return FileText(
        path=path,
        content=str(payload.get("content") or ""),
        version=int(payload.get("version") or 0),
        exists=bool(payload.get("exists")),
    )


def writable(*, transport: Transport) -> tuple[bool, str]:
    """Whether this deployment accepts edits, and what it says about it."""
    status, payload = transport.get("/config/editing")
    if status != 200 or not isinstance(payload, dict):
        return True, ""
    return bool(payload.get("editable")), str(payload.get("mode") or "")


def set_file(
    path: str,
    content: str,
    *,
    transport: Transport,
    force: bool = False,
) -> dict[str, Any]:
    """Write one file, carrying the version it was read at."""
    editable, mode = writable(transport=transport)
    if not editable:
        raise ReadOnlyDeployment(
            f"This deployment is {mode or 'read-only'}: the write routes are "
            "not registered, so nothing was sent. Edit the file in the "
            "configuration tree, or start the agent with "
            "UI_CONFIG_MODE=readwrite."
        )

    base_version: int | None = None
    if not force:
        base_version = show_file(path, transport=transport).version

    status, payload = transport.put(
        "/config/edit",
        {"path": path, "content": content, "base_version": base_version},
    )
    if status == 404:
        raise ReadOnlyDeployment(
            f"The agent has no write route for {path}. Either this deployment "
            "is read-only or the path is not in its editable set."
        )
    if status == 409:
        raise ConfigFailed(
            f"{path} changed since it was read: {_why(payload)}. Read it "
            "again, reapply the change, and write it again."
        )
    if status == 422:
        raise ConfigFailed(f"That edit was refused: {_why(payload)}")
    if status not in (200, 201):
        raise ConfigFailed(f"Could not write {path} ({status}): {_why(payload)}")
    return payload if isinstance(payload, dict) else {}


class SchemaMismatch(ConfigFailed):
    """This build and that tree do not read the same layout."""


@dataclass(frozen=True)
class Schema:
    """The config schema versions the agent supports and the one declared."""

    current: int
    oldest_supported: int
    declared: int | None
    deprecated: bool = False

    @property
    def readable(self) -> bool:
        """Whether this build can load the tree it is pointed at."""
        if self.declared is None:
            return True
        return self.oldest_supported <= self.declared <= self.current


def schema_of(*, transport: Transport) -> Schema:
    """Which layouts the agent reads, and which one its tree claims."""
    status, payload = transport.get("/admin/config")
    if status != 200 or not isinstance(payload, dict):
        raise ConfigFailed(f"Could not read the agent's schema ({status})")
    found = payload.get("schema")
    if not isinstance(found, dict):
        return Schema(current=0, oldest_supported=0, declared=None)
    return Schema(
        current=int(found.get("current") or 0),
        oldest_supported=int(found.get("oldest_supported") or 0),
        declared=(None if found.get("declared") is None else int(found["declared"])),
        deprecated=bool(found.get("deprecated")),
    )


def _agree(*, transport: Transport) -> Schema:
    """The schema check both of these commands run first."""
    schema = schema_of(transport=transport)
    if not schema.readable:
        raise SchemaMismatch(
            f"this agent reads schema versions {schema.oldest_supported} to "
            f"{schema.current} and its tree declares {schema.declared}. "
            "Upgrade the image, or migrate the tree with "
            "`make migrate-config DIR=<path>`."
        )
    return schema


@dataclass(frozen=True)
class Drift:
    """One config path where the overlay differs from the shipped baseline."""

    path: str
    baseline: str
    overlay: str
    version: int
    author: str = ""


def drifted(*, transport: Transport) -> list[Drift]:
    """Every path this deployment has edited away from its tree."""
    _agree(transport=transport)
    status, payload = transport.get("/config/drift")
    if status != 200 or not isinstance(payload, dict):
        raise ConfigFailed(f"Could not read what has been edited ({status})")
    return [
        Drift(
            path=str(one.get("path") or ""),
            baseline=str(one.get("baseline") or ""),
            overlay=str(one.get("overlay") or ""),
            version=int(one.get("version") or 0),
            author=str(one.get("author") or ""),
        )
        for one in (payload.get("paths") or [])
        if isinstance(one, dict)
    ]


def diff(*, transport: Transport) -> str:
    """What the running agent reads that its tree does not say."""
    import difflib

    out: list[str] = []
    for one in drifted(transport=transport):
        out.extend(
            difflib.unified_diff(
                one.baseline.splitlines(keepends=True),
                one.overlay.splitlines(keepends=True),
                fromfile=f"a/{one.path}",
                tofile=f"b/{one.path}  (v{one.version}"
                + (f", {one.author}" if one.author else "")
                + ")",
                n=3,
            )
        )
    return "".join(out)


@dataclass(frozen=True)
class Rendered:
    """Which config files were written out and which were skipped."""

    written: list[str]
    skipped: list[str] = field(default_factory=list)


def render(*, transport: Transport, out: Any) -> Rendered:
    """Write the tree as the agent currently reads it."""
    from pathlib import Path

    _agree(transport=transport)
    root = Path(out)
    written: list[str] = []
    refused: list[str] = []
    for one in list_files(transport=transport):
        try:
            text = show_file(one.path, transport=transport)
        except ConfigFailed:
            refused.append(one.path)
            continue
        if not text.exists:
            continue
        where = (root / one.path).resolve()
        if not str(where).startswith(str(root.resolve())):
            raise ConfigFailed(f"{one.path} would be written outside {root}")
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text.content)
        written.append(one.path)
    return Rendered(written=written, skipped=refused)


def _why(payload: Any) -> str:
    """The human-readable reason out of an error payload."""
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("detail") or payload)
    return str(payload)
