"""What each extension costs, and how often it says no."""

from __future__ import annotations

import functools
import threading
import time
from collections import deque
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


class ExtensionTiming:
    """Per-extension call counts, durations and refusals."""

    WINDOW = 200

    def __init__(self) -> None:
        """Start with nothing recorded."""
        self._lock = threading.Lock()
        self._seen: dict[str, deque[float]] = {}
        self._calls: dict[str, int] = {}
        self._refusals: dict[str, int] = {}

    def record(self, path: str, *, seconds: float, refused: bool = False) -> None:
        """One call to one extension. A refusal still took time."""
        with self._lock:
            window = self._seen.setdefault(path, deque(maxlen=self.WINDOW))
            window.append(seconds)
            self._calls[path] = self._calls.get(path, 0) + 1
            if refused:
                self._refusals[path] = self._refusals.get(path, 0) + 1

    def summary(self, path: str) -> dict[str, Any] | None:
        """What is known about one extension, or None if it never ran."""
        with self._lock:
            window = self._seen.get(path)
            if not window:
                return None
            calls = self._calls.get(path, 0)
            refusals = self._refusals.get(path, 0)
            return {
                "calls": calls,
                "refusals": refusals,
                "refusal_rate": refusals / calls if calls else 0.0,
                "average_ms": (sum(window) / len(window)) * 1000,
                "slowest_ms": max(window) * 1000,
            }

    def all(self) -> dict[str, dict[str, Any]]:
        """Every extension that has run, with its figures."""
        with self._lock:
            paths = list(self._seen)
        found = {}
        for path in paths:
            summary = self.summary(path)
            if summary is not None:
                found[path] = summary
        return found


timing = ExtensionTiming()

_HOOKS = (
    "before_agent",
    "abefore_agent",
    "before_model",
    "abefore_model",
    "wrap_model_call",
    "awrap_model_call",
    "after_model",
    "aafter_model",
    "wrap_tool_call",
    "awrap_tool_call",
)


def _timed(call: Any, path: str) -> Any:
    """`call` wrapped to record how long it takes and whether it refused."""

    @functools.wraps(call)
    def timed(*args: Any, **kwargs: Any) -> Any:
        """Call through, recording the time taken."""
        started = time.perf_counter()
        try:
            found = call(*args, **kwargs)
        except Exception:
            timing.record(path, seconds=time.perf_counter() - started, refused=True)
            raise
        timing.record(path, seconds=time.perf_counter() - started)
        return found

    return timed


def _timed_async(call: Any, path: str) -> Any:
    """`call` wrapped to record how long it takes and whether it refused."""

    @functools.wraps(call)
    async def timed(*args: Any, **kwargs: Any) -> Any:
        """Await the call, recording the time taken."""
        started = time.perf_counter()
        try:
            found = await call(*args, **kwargs)
        except Exception:
            timing.record(path, seconds=time.perf_counter() - started, refused=True)
            raise
        timing.record(path, seconds=time.perf_counter() - started)
        return found

    return timed


def timed_extension(made: Any, path: str) -> Any:
    """The extension, with its hooks counted and timed."""
    import inspect

    for name in _HOOKS:
        hook = getattr(made, name, None)
        if hook is None or not callable(hook):
            continue
        maker = _timed_async if inspect.iscoroutinefunction(hook) else _timed
        try:
            setattr(made, name, maker(hook, path))
        except AttributeError:
            logger.debug("Could not time '%s' on extension '%s'", name, path)

    return made
