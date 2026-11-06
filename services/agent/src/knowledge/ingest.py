"""The corpus an agent ships with, read from its configuration tree."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.src.knowledge.chunking import chunk_markdown
from agent.src.knowledge.scopes import Scope
from agent.src.knowledge.store import Document
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

READABLE = (".md", ".markdown", ".txt", ".rst")

PREFIX = "corpus:"

TEAMS_DIR = "teams"

_DEFAULT_MAX_BYTES = 5 * 1024 * 1024

_MAX_PARTS = 200


@dataclass
class Progress:
    """How far an ingest has got."""

    total: int = 0
    done: int = 0
    current: str = ""


@dataclass
class Synced:
    """What a corpus sync ingested, removed and skipped."""

    ingested: int = 0
    removed: int = 0
    skipped: list[str] = field(default_factory=list)


def _id_for(root: Path, path: Path) -> str:
    """Stable across runs, and it says where the document came from."""
    return f"{PREFIX}{path.relative_to(root).as_posix()}"


def _team_of(root: Path, path: Path) -> str | None:
    """Which team a file belongs to, by where it sits."""
    parts = path.relative_to(root).parts
    if not parts or parts[0] != TEAMS_DIR:
        return None
    return parts[1] if len(parts) > 2 else ""


def sync_corpus(
    root: Path | None,
    *,
    store: Any,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
    on_progress: Callable[[Progress], None] | None = None,
) -> Synced:
    """Make the store match the tree, in both directions."""
    found = Synced()

    files = (
        sorted(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in READABLE
        )
        if root is not None and root.is_dir()
        else []
    )

    progress = Progress(total=len(files))
    seen: set[str] = set()

    for path in files:
        progress.current = path.name
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            found.skipped.append(f"{path.name}: could not be read ({error})")
            continue

        oversize = len(text.encode("utf-8")) > max_bytes

        if not text.strip():
            found.skipped.append(f"{path.name}: empty")
            continue

        document_id = _id_for(root, path) if root is not None else path.name
        team = _team_of(root, path) if root is not None else None
        if team == "":
            found.skipped.append(
                f"{path.name}: directly inside {TEAMS_DIR}/, so it belongs to no team"
            )
            continue

        title = path.stem.replace("_", " ").replace("-", " ")
        parts = (
            chunk_markdown(text, size=chunk_size, overlap=chunk_overlap)
            if oversize
            else [text]
        )
        if len(parts) > _MAX_PARTS:
            found.skipped.append(
                f"{path.name}: kept the first {_MAX_PARTS} parts of "
                f"{len(parts)}; the rest is not searchable"
            )
            parts = parts[:_MAX_PARTS]

        for index, part in enumerate(parts):
            part_id = document_id if len(parts) == 1 else f"{document_id}#{index}"
            seen.add(part_id)
            store.add(
                Document(
                    id=part_id,
                    text=part,
                    scope=Scope.TEAM if team else Scope.AGENT,
                    team=team or None,
                    title=title,
                    metadata={"path": str(path)},
                )
            )
        found.ingested += 1

        progress.done += 1
        if on_progress is not None:
            on_progress(Progress(**progress.__dict__))

    found.removed = store.forget_corpus(prefix=PREFIX, keeping=seen)
    if found.skipped:
        logger.warning(
            "Corpus skipped %d file(s): %s", len(found.skipped), found.skipped
        )
    return found
