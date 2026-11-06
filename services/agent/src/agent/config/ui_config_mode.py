"""Whether this deployment may be reconfigured from a browser."""

from __future__ import annotations

import os

MODES: tuple[str, ...] = ("readonly", "readwrite")

VARIABLE = "UI_CONFIG_MODE"

_EDITABLE = (
    "config/agent/PROMPT.md",
    "config/agent/runtime/agent.yaml",
    "config/agent/runtime/router.yaml",
    "config/agent/integrations/mcp.json",
    "config/agent/subagents/",
    "config/agent/skills/",
    "config/agent/evals/",
)


def mode_from(value: str | None) -> str:
    """The mode this value names, or read-only if it names none."""
    asked = (value or "").strip().lower()
    return asked if asked in MODES else "readonly"


def editing_allowed(value: str | None) -> bool:
    """Whether this value permits configuration to be written."""
    return mode_from(value) == "readwrite"


def editing_allowed_now() -> bool:
    """The same question, of the environment as it stands."""
    return editing_allowed(os.environ.get(VARIABLE))


EXTRA_VARIABLE = "UI_CONFIG_EDITABLE_EXTRA"

_ALLOWED_ROOTS = ("config/agent/",)


def _extra_paths(value: str | None) -> tuple[str, ...]:
    """Paths from the environment, after refusing the dangerous ones."""
    out: list[str] = []
    for raw in (value or "").split(","):
        candidate = raw.strip()
        if not candidate or ".." in candidate:
            continue
        if not any(candidate.startswith(root) for root in _ALLOWED_ROOTS):
            continue
        out.append(candidate)
    return tuple(out)


def editable_paths() -> tuple[str, ...]:
    """What may be written when the deployment is writable."""
    extra = _extra_paths(os.environ.get(EXTRA_VARIABLE))
    return _EDITABLE + tuple(p for p in extra if p not in _EDITABLE)
