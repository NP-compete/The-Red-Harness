"""Usage as a file somebody can open."""

from __future__ import annotations

import csv
import io
from typing import Any

_EXECUTABLE = ("=", "+", "-", "@", "\t", "\r")


def as_csv(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    """Records as CSV, safe to open."""
    header = columns if columns is not None else _columns_of(rows)
    if not header:
        return ""

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_cell(row.get(name)) for name in header])
    return out.getvalue()


def _columns_of(rows: list[dict[str, Any]]) -> list[str]:
    """Every column any row has, first-seen order."""
    seen: dict[str, None] = {}
    for row in rows:
        for name in row:
            seen.setdefault(name, None)
    return list(seen)


def _cell(value: Any) -> Any:
    """One value, rendered so a spreadsheet reads it and nothing more."""
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, str):
        return value
    if value.startswith(_EXECUTABLE):
        return f"'{value}"
    return value
