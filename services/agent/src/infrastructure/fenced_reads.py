"""Marking file content that came from outside the deployment."""

from __future__ import annotations

from typing import Any

from agent.src.security.fencing import fence


def _fenced(result: Any, file_path: str) -> Any:
    """The same result, with its text marked as material to read."""
    if result is None or getattr(result, "error", None):
        return result

    file_data = getattr(result, "file_data", None)
    if not isinstance(file_data, dict):
        return result

    content = file_data.get("content")
    if not isinstance(content, str) or not content:
        return result

    file_data["content"] = fence(content, source=file_path)
    return result


class FencedReadBackend:
    """A filesystem backend whose reads arrive marked as data."""

    def __init__(self, inner: Any, only: tuple[str, ...] | None = None) -> None:
        """Wrap `inner`, fencing reads under `only` if it is given."""
        self._inner = inner
        self._only = only

    def _outside(self, file_path: str) -> bool:
        """Whether `file_path` holds content from outside the agent."""
        if self._only is None:
            return True
        return any(file_path.startswith(prefix) for prefix in self._only)

    def read(self, file_path: str, *args: Any, **kwargs: Any) -> Any:
        """Read `file_path`, fencing it if it comes from outside."""
        found = self._inner.read(file_path, *args, **kwargs)
        return _fenced(found, file_path) if self._outside(file_path) else found

    async def aread(self, file_path: str, *args: Any, **kwargs: Any) -> Any:
        """Read `file_path`, fencing it if it comes from outside."""
        found = await self._inner.aread(file_path, *args, **kwargs)
        return _fenced(found, file_path) if self._outside(file_path) else found

    def __getattr__(self, name: str) -> Any:
        """Fall through to the wrapped backend."""
        return getattr(self._inner, name)


def fenced(inner: Any, *, only: tuple[str, ...] | None = None) -> Any:
    """The same backend, with outside content marked on the way out."""

    def _read(self: Any, file_path: str, *args: Any, **kwargs: Any) -> Any:
        """Read through the base backend, fencing outside content."""
        found = super(made, self).read(file_path, *args, **kwargs)  # type: ignore[arg-type]
        return _fenced(found, file_path) if _outside(file_path, only) else found

    async def _aread(self: Any, file_path: str, *args: Any, **kwargs: Any) -> Any:
        """Read through the base backend, fencing outside content."""
        found = await super(made, self).aread(file_path, *args, **kwargs)  # type: ignore[arg-type]
        return _fenced(found, file_path) if _outside(file_path, only) else found

    made = type(
        f"Fenced{type(inner).__name__}",
        (type(inner),),
        {"read": _read, "aread": _aread},
    )
    inner.__class__ = made
    return inner


def _outside(file_path: str, only: tuple[str, ...] | None) -> bool:
    """Whether this path carries content from outside the deployment."""
    if only is None:
        return True
    return any(file_path.startswith(prefix) for prefix in only)
