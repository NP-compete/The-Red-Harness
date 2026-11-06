"""Replaying a recorded conversation instead of paying for it (E27-T3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CASSETTES = Path(__file__).resolve().parent / "cassettes"


class CassetteMiss(KeyError):
    """No recording for this conversation."""


def key_for(messages: list[Any]) -> str:
    """A stable name for one conversation."""
    said = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        said.append(f"{message.get('role') or ''}:{str(content or '').strip()}")
    return hashlib.sha256("\n".join(said).encode()).hexdigest()[:16]


def load(path: Path | str) -> dict[str, Any]:
    where = Path(path)
    if not where.is_file():
        raise FileNotFoundError(f"no cassette at {where}")
    found = json.loads(where.read_text())
    if not isinstance(found, dict):
        raise ValueError(f"{where} is not a cassette")
    return found.get("exchanges") or {}


def answer_from(cassette: dict[str, Any], messages: list[Any]) -> dict[str, Any]:
    """The recorded reply, or a miss naming what to record."""
    key = key_for(messages)
    found: dict[str, Any] | None = cassette.get(key)
    if found is None:
        last = ""
        for message in reversed(messages or []):
            if isinstance(message, dict) and message.get("role") == "user":
                last = str(message.get("content") or "")[:80]
                break
        raise CassetteMiss(
            f"no recording for {key} (last asked: {last!r}). "
            "Record it with `make cassette-record`, or check the "
            "conversation is the one the cassette was made from."
        )
    return found


def record(path: Path | str, messages: list[Any], reply: dict[str, Any]) -> str:
    """Add one exchange to a cassette, keeping the rest."""
    where = Path(path)
    where.parent.mkdir(parents=True, exist_ok=True)
    whole: dict[str, Any] = {"exchanges": {}}
    if where.is_file():
        try:
            whole = json.loads(where.read_text())
        except ValueError:
            whole = {"exchanges": {}}
    key = key_for(messages)
    whole.setdefault("exchanges", {})[key] = reply
    where.write_text(json.dumps(whole, indent=2, sort_keys=True) + "\n")
    return key
