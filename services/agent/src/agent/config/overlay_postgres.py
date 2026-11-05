"""An overlay whose edits outlive the process that made them."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agent.src.agent.config.overlay import NothingToRevertTo, Version
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_TABLE = "config_overlay"


def _now() -> str:
    """The current UTC time, ISO-formatted."""
    return datetime.now(timezone.utc).isoformat()


class PostgresOverlay:
    """Append-only configuration edits, kept in a table."""

    def __init__(self, dsn: str, table: str = _TABLE) -> None:
        """Bind the overlay to a DSN and table, with nothing yet loaded."""
        self._dsn = dsn
        self.table = table
        self._rows: dict[str, list[Version]] = {}
        self._generation = 0

    def _connect(self) -> Any:
        """Open a connection to the overlay's database."""
        import psycopg

        return psycopg.connect(self._dsn, connect_timeout=5)

    def ensure_table(self) -> None:
        """Create the table if it is not there."""
        with self._connect() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    path     TEXT        NOT NULL,
                    version  INTEGER     NOT NULL,
                    content  TEXT,
                    author   TEXT        NOT NULL,
                    at       TEXT        NOT NULL,
                    PRIMARY KEY (path, version)
                )
                """
            )
            conn.commit()
        self.refresh()

    def refresh(self) -> None:
        """Re-read every row, so another pod's edits arrive."""
        rows: dict[str, list[Version]] = {}
        with self._connect() as conn:
            found = conn.execute(
                f"SELECT path, version, content, author, at FROM {self.table} "
                "ORDER BY path, version"
            ).fetchall()

        for path, version, content, author, at in found:
            rows.setdefault(path, []).append(
                Version(
                    path=path,
                    content=content,
                    version=version,
                    author=author,
                    at=at,
                )
            )

        self._rows = rows
        self._generation = sum(len(one) for one in rows.values())

    def _write(self, path: str, content: str | None, author: str) -> Version:
        """Append a new version of `path` and bump the generation."""
        if not author or not author.strip():
            raise ValueError("an edit has to record who made it")

        written = Version(
            path=path,
            content=content,
            version=len(self._rows.get(path) or []) + 1,
            author=author.strip(),
            at=_now(),
        )

        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO {self.table} (path, version, content, author, at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    written.path,
                    written.version,
                    written.content,
                    written.author,
                    written.at,
                ),
            )
            conn.commit()

        self.refresh()
        return self._require(path, written.version)

    def apply(self, path: str, content: str, *, author: str) -> Version:
        """Record `content` as the new state of `path`."""
        return self._write(path, content, author)

    def adopt_baseline(self, path: str, *, author: str) -> Version:
        """Drop the override on `path` and fall back to the shipped file."""
        return self._write(path, None, author)

    def revert(self, path: str, *, to: int, author: str) -> Version:
        """Record the content of version `to` as a new version of `path`."""
        wanted = next(
            (one for one in self._rows.get(path, []) if one.version == to), None
        )
        if wanted is None:
            raise NothingToRevertTo(f"{path} has no version {to} to go back to")
        return self._write(path, wanted.content, author)

    @property
    def generation(self) -> int:
        """How many times anything in the overlay has changed."""
        return self._generation

    def current(self, path: str) -> str | None:
        """The overriding content of `path`, or `None` if it is not overridden."""
        kept = self._rows.get(path) or []
        return kept[-1].content if kept else None

    def at_version(self, path: str, version: int) -> Version:
        """The recorded version `version` of `path`."""
        return self._require(path, version)

    def history(self, path: str) -> list[Version]:
        """Every recorded version of `path`, oldest first."""
        return list(self._rows.get(path) or [])

    def overridden(self) -> list[str]:
        """Paths the overlay currently overrides."""
        return sorted(path for path in self._rows if self.current(path) is not None)

    def _require(self, path: str, version: int) -> Version:
        """Version `version` of `path`, or raise if it was never recorded."""
        found = next(
            (one for one in self._rows.get(path, []) if one.version == version), None
        )
        if found is None:
            raise NothingToRevertTo(f"{path} has no version {version}")
        return found
