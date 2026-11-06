"""Split a document into retrievable pieces."""

from __future__ import annotations

import re

_BOUNDARIES = ("\n\n", "\n", ". ", " ")


def chunk_text(text: str, *, size: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks of roughly ``size`` characters."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            window_start = max(start, end - size // 4)
            for boundary in _BOUNDARIES:
                found = text.rfind(boundary, window_start, end)
                if found > start:
                    end = found + len(boundary)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break
        start = max(start + 1, end - overlap)

    return chunks


_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def chunk_markdown(text: str, *, size: int = 1200, overlap: int = 200) -> list[str]:
    """Chunk markdown along headings, then by size within each section."""
    matches = list(_HEADING.finditer(text))
    if not matches:
        return chunk_text(text, size=size, overlap=overlap)

    sections: list[str] = []
    if matches[0].start() > 0:
        sections.append(text[: matches[0].start()])

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(text[match.start() : end])

    chunks: list[str] = []
    for section in sections:
        chunks.extend(chunk_text(section, size=size, overlap=overlap))
    return chunks
