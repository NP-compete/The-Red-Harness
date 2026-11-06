"""Filename and content checks for uploaded files."""

from __future__ import annotations

import re
import unicodedata

from agent.src.settings import settings

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_COLLAPSE = re.compile(r"_{2,}")

_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

MAX_NAME_LENGTH = settings.ATTACHMENT_MAX_NAME_LENGTH


def sanitise_filename(raw: str) -> str:
    """Reduce a user-supplied filename to something safe to join."""
    name = unicodedata.normalize("NFKC", raw or "")

    name = name.replace("\\", "/").split("/")[-1]

    name = name.replace("\x00", "")

    name = _SAFE_CHARS.sub("_", name)
    name = _COLLAPSE.sub("_", name).strip("._-")

    if not name:
        return "upload"

    stem, _, suffix = name.rpartition(".")
    if stem and stem.lower() in _RESERVED:
        stem = f"{stem}_file"
        name = f"{stem}.{suffix}" if suffix else stem
    elif not stem and name.lower() in _RESERVED:
        name = f"{name}_file"

    if len(name) > MAX_NAME_LENGTH:
        stem, _, suffix = name.rpartition(".")
        keep = MAX_NAME_LENGTH - len(suffix) - 1 if suffix else MAX_NAME_LENGTH
        name = f"{stem[:keep]}.{suffix}" if suffix else name[:MAX_NAME_LENGTH]

    return name


def unique_name(name: str, taken: set[str]) -> str:
    """Avoid clobbering an existing attachment with the same name."""
    if name not in taken:
        return name
    stem, _, suffix = name.rpartition(".")
    if not stem:
        stem, suffix = name, ""
    for n in range(2, 1000):
        candidate = f"{stem}-{n}.{suffix}" if suffix else f"{stem}-{n}"
        if candidate not in taken:
            return candidate
    raise ValueError("too many files with the same name")
