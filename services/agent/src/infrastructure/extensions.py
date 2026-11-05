"""Middleware a deployment adds for itself, and what happens if it is missing.

An extension is imported and run **in this process**, with the same
privileges as the agent: it can read every secret in the environment,
reach anything the pod can reach, and see every message that crosses
the middleware chain. There is no sandbox here and none is implied.
Adding one is a decision to trust that code exactly as much as the
agent's own, which is why `required` is explicit — a deployment that
cannot start without its extension should say so rather than quietly
run with less than it asked for.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_FAILURE_MODES = {"closed": True, "open": False}


class ExtensionUnavailable(RuntimeError):
    """A required extension could not be loaded, so the run must not start."""


@dataclass(frozen=True)
class Extension:
    """One declared extension, and whether the agent needs it."""

    path: str
    """Refuse to run without it, rather than running unprotected."""
    required: bool

    def _make(self) -> Any:
        """Import the extension and build it."""
        module_path, _, attr_name = self.path.partition(":")
        module = importlib.import_module(module_path)
        found = getattr(module, attr_name)
        return found() if callable(found) else found

    def status(self) -> tuple[bool, str]:
        """Whether it loads, and why not — without raising either way."""
        try:
            self._make()
        except Exception as error:
            return False, f"{self.path}: {error}"
        return True, ""

    def load(self) -> Any | None:
        """The middleware, or None for an optional one that is absent."""
        try:
            made = self._make()
        except Exception as error:
            if self.required:
                raise ExtensionUnavailable(
                    f"The extension '{self.path}' could not be loaded: {error}. "
                    "It is declared as required, so the agent will not start "
                    "without it. Mark it 'on_failure: open' if the run should "
                    "carry on regardless."
                ) from error
            logger.warning(
                "Optional extension '%s' could not be loaded and was skipped: %s",
                self.path,
                error,
            )
            return None

        logger.info("Loaded extension '%s' (required=%s)", self.path, self.required)

        from agent.src.infrastructure.extension_metrics import timed_extension

        return timed_extension(made, self.path)


def declared_extension(entry: str | dict[str, Any]) -> Extension:
    """Read one declared extension, refusing anything ambiguous."""
    if isinstance(entry, str):
        path, required = entry, True
    else:
        path = str(entry.get("path") or "").strip()
        if not path:
            raise ValueError("Every extension needs a path, as 'module:Attribute'")
        mode = str(entry.get("on_failure", "closed")).strip().lower()
        if mode not in _FAILURE_MODES:
            raise ValueError(
                f"'{mode}' is not a usable on_failure for '{path}' — "
                "use 'closed' to refuse without it, or 'open' to carry on"
            )
        required = _FAILURE_MODES[mode]

    module_path, sep, attr_name = path.partition(":")
    if not sep or not module_path.strip() or not attr_name.strip():
        raise ValueError(f"'{path}' must name an attribute, as 'module:Attribute'")

    return Extension(path=path, required=required)
