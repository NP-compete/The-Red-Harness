"""Resolve logical config names to files on disk."""

from __future__ import annotations

import os
from pathlib import Path

from agent._root import CONFIG_ROOT
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_CANDIDATES: dict[str, tuple[str, ...]] = {
    "prompt": ("PROMPT.md",),
    "headless_prompt": ("HEADLESS_PROMPT.md",),
    "mcp": ("integrations/mcp.json", "mcp.json"),
    "channels": ("integrations/channels.yaml",),
    "mcp_server": ("integrations/mcp_server.yaml",),
    "agent": ("runtime/agent.yaml", "agent.yaml"),
    "observability": ("runtime/observability.yaml", "observability.yaml"),
    "pii": ("runtime/pii.yaml", "pii.yaml"),
    "router": ("runtime/router.yaml", "router.yaml"),
    "ui": ("runtime/ui.yaml", "ui.yaml"),
    "filesystem": ("runtime/filesystem.yaml", "filesystem.yaml"),
    "memory_instructions": ("prompts/memory_instructions.md", "memory_instructions.md"),
    "guardrails": ("guardrails/guardrails.yaml", "runtime/guardrails.yaml"),
}

_DIR_CANDIDATES: dict[str, tuple[str, ...]] = {
    "skills": ("skills",),
    "subagents": ("subagents",),
    "policies": ("compliance/policies",),
    "evals": ("evals",),
}

_warned: set[str] = set()


def config_root() -> Path:
    """The single mounted config directory."""
    return Path(
        os.getenv(
            "CONFIG_PATH",
            str(CONFIG_ROOT),
        )
    )


def _resolve(
    name: str, candidates: dict[str, tuple[str, ...]], is_dir: bool
) -> Path | None:
    """First candidate that exists, warning when it is not the preferred one."""
    options = candidates.get(name)
    if not options:
        raise KeyError(f"Unknown config name: {name!r}")

    root = config_root()
    exists = Path.is_dir if is_dir else Path.is_file

    for index, relative in enumerate(options):
        path = root / relative
        if exists(path):
            if index > 0 and name not in _warned:
                _warned.add(name)
                logger.warning(
                    "Config '%s' found at the legacy path %r — rename to %r; "
                    "the old path will stop being read in a future version.",
                    name,
                    relative,
                    options[0],
                )
            return path
    return None


def candidates_for(name: str) -> tuple[str, ...]:
    """The accepted relative paths for *name*, preferred first."""
    options = _CANDIDATES.get(name) or _DIR_CANDIDATES.get(name)
    if not options:
        raise KeyError(f"Unknown config name: {name!r}")
    return options


def config_file(name: str) -> Path | None:
    """Path to a config file, or None when the agent does not define it."""
    return _resolve(name, _CANDIDATES, is_dir=False)


def config_dir(name: str) -> Path | None:
    """Path to a config directory, or None when absent."""
    return _resolve(name, _DIR_CANDIDATES, is_dir=True)


def preferred_path(name: str) -> Path:
    """Where a config file *should* live, whether or not it exists yet."""
    options = _CANDIDATES.get(name) or _DIR_CANDIDATES.get(name)
    if not options:
        raise KeyError(f"Unknown config name: {name!r}")
    return config_root() / options[0]


def describe_layout() -> dict[str, dict[str, object]]:
    """Every logical name, where it resolved, and whether that is legacy."""
    report: dict[str, dict[str, object]] = {}
    for name, options in {**_CANDIDATES, **_DIR_CANDIDATES}.items():
        is_dir = name in _DIR_CANDIDATES
        resolved = _resolve(name, _DIR_CANDIDATES if is_dir else _CANDIDATES, is_dir)
        relative = (
            str(resolved.relative_to(config_root())) if resolved is not None else None
        )
        report[name] = {
            "path": relative,
            "preferred": options[0],
            "legacy": relative is not None and relative != options[0],
            "present": resolved is not None,
        }
    return report
