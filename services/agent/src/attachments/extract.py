"""Turn an uploaded file into text the model can read."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent.utils.pylogger import get_python_logger

if TYPE_CHECKING:
    from agent.src.attachments.config import ExtractionConfig

logger = get_python_logger()

_TEXT_SUFFIXES = {
    "txt",
    "md",
    "csv",
    "tsv",
    "json",
    "yaml",
    "yml",
    "log",
    "xml",
    "html",
}
_IMAGE_SUFFIXES = {"png", "jpg", "jpeg", "gif", "webp"}

_OFFICE_SUFFIXES = {"docx", "xlsx", "pptx"}

_MULTIMODAL_SUFFIXES = {
    "pdf",
    "pptx",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "mp3",
    "wav",
    "ogg",
    "mp4",
    "mov",
    "webm",
}


def needs_base64(filename: str) -> bool:
    """True when the model receives this file as binary, not as text."""
    return suffix_of(filename) in _MULTIMODAL_SUFFIXES


def suffix_of(filename: str) -> str:
    """Lower-cased file extension, or an empty string when there is none."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def is_image(filename: str) -> bool:
    """Does this filename look like an image the model can read directly?"""
    return suffix_of(filename) in _IMAGE_SUFFIXES


def extract_text(filename: str, data: bytes, max_chars: int) -> tuple[str, bool]:
    """Return ``(text, is_complete)`` for an uploaded file."""
    suffix = suffix_of(filename)

    if suffix in _TEXT_SUFFIXES:
        text = data.decode("utf-8", errors="replace")
    elif suffix == "pdf":
        text = _extract_pdf(data)
    elif suffix == "docx":
        text = _extract_docx(data)
    elif suffix == "xlsx":
        text = _extract_xlsx(data)
    elif suffix == "pptx":
        text = _extract_pptx(data)
    else:
        return "", True

    if len(text) > max_chars:
        return text[:max_chars], False
    return text, True


def _extract_pdf(data: bytes) -> str:
    """Best-effort PDF text."""
    try:
        import io

        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _extract_docx(data: bytes) -> str:
    """Paragraphs and table cells from a Word document."""
    try:
        import io

        from docx import Document
    except ImportError:
        return ""

    try:
        document = Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs if p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_xlsx(data: bytes) -> str:
    """Cell values, sheet by sheet."""
    try:
        import io

        from openpyxl import load_workbook
    except ImportError:
        return ""

    try:
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet in book.worksheets:
            parts.append(f"# {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    parts.append(" | ".join(cells))
        book.close()
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_pptx(data: bytes) -> str:
    """Text frames from every slide."""
    try:
        import io

        from pptx import Presentation
    except ImportError:
        return ""

    try:
        deck = Presentation(io.BytesIO(data))
        parts: list[str] = []
        for number, slide in enumerate(deck.slides, start=1):
            parts.append(f"# Slide {number}")
            for shape in slide.shapes:
                text = getattr(shape, "text", "")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts)
    except Exception:
        return ""


@dataclass(frozen=True)
class Extraction:
    """What was read, and by what."""

    text: str
    complete: bool
    engine: str = "builtin"
    degraded: str = ""


async def extract_best(
    filename: str,
    data: bytes,
    max_chars: int,
    extraction: ExtractionConfig | None = None,
) -> Extraction:
    """Extract with the configured engine, degrading to the built-in one."""
    from agent.src.attachments.engines import (
        SUSPECT_CHARS,
        ExtractionUnavailable,
        extract_remote,
    )

    if extraction is None or not extraction.handles(filename, len(data)):
        text, complete = extract_text(filename, data, max_chars)
        return Extraction(text=text, complete=complete)

    try:
        remote = await extract_remote(filename, data, extraction)
    except ExtractionUnavailable as exc:
        logger.warning("Extraction engine failed for %s: %s", filename, exc)
        if not extraction.fallback:
            raise
        text, complete = extract_text(filename, data, max_chars)
        return Extraction(
            text=text,
            complete=complete,
            degraded=f"{extraction.engine} unavailable, read with built-in parser",
        )

    text, engine = remote.text, remote.engine

    if len(text.strip()) < SUSPECT_CHARS:
        local, _ = extract_text(filename, data, max_chars)
        if len(local.strip()) > len(text.strip()):
            logger.info(
                "Built-in parser beat %s on %s (%d vs %d chars)",
                engine,
                filename,
                len(local),
                len(text),
            )
            text, engine = local, "builtin"

    if len(text) > max_chars:
        return Extraction(text=text[:max_chars], complete=False, engine=engine)
    return Extraction(text=text, complete=True, engine=engine)


def describe(
    filename: str,
    size: int,
    text: str,
    complete: bool,
    engine: str = "builtin",
    degraded: str = "",
) -> str:
    """One line of provenance for the model, above any extracted text."""
    kind = "image" if is_image(filename) else suffix_of(filename) or "file"
    size_kb = max(1, size // 1024)
    notes = []
    if engine != "builtin":
        notes.append(f"read by {engine}")
    if degraded:
        notes.append(degraded)
    tail = f" — {', '.join(notes)}" if notes else ""

    if not text:
        return (
            f"[attached {kind}: {filename}, {size_kb} KB — "
            f"content not extractable as text"
            f"{'; ' + degraded if degraded else ''}]"
        )
    cut = "" if complete else " (truncated)"
    return f"[attached {kind}: {filename}, {size_kb} KB{cut}{tail}]"
