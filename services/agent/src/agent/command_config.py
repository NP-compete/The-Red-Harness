"""Commands a deployment declares for itself, read from configuration."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from agent.src.agent.commands import Command

_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")

_ALLOWED = frozenset({"name", "help", "prompt"})


def load_declared_commands(path: Path) -> list[Command]:
    """Every command this deployment has added, or none."""
    if not path.is_file():
        return []

    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as error:
        raise ValueError(
            f"{path} is not readable as a command list: {error}"
        ) from error

    declared: list[Command] = []
    for entry in raw.get("commands") or []:
        declared.append(_command(path, entry or {}))
    return declared


def _shipped_names() -> frozenset[str]:
    from agent.src.agent.command_catalogue import SHIPPED

    return frozenset(command.name for command in SHIPPED)


def _command(path: Path, entry: dict) -> Command:
    unknown = sorted(set(entry) - _ALLOWED)
    if unknown:
        raise ValueError(
            f"{path}: a command holds a name, one line of help and a prompt, "
            f"and nothing else — remove {', '.join(unknown)}. A command cannot "
            "approve anything, choose its own tools or lift a budget; it "
            "expands to a sentence that goes through every check a typed "
            "message does."
        )

    name = str(entry.get("name") or "").strip().lstrip("/")
    if not name:
        raise ValueError(f"{path}: every command needs a name")
    if not _NAME.match(name):
        raise ValueError(
            f"{path}: '{name}' is not a usable name — one word, letters, "
            "digits and hyphens"
        )

    if name in _shipped_names():
        raise ValueError(
            f"{path}: '{name}' is already a command this agent ships; "
            "give yours a name of its own"
        )

    help_text = str(entry.get("help") or "").strip()
    if not help_text:
        raise ValueError(f"{path}: '{name}' needs one line of help to be findable")

    prompt = str(entry.get("prompt") or "").strip()
    if not prompt:
        raise ValueError(f"{path}: '{name}' needs a prompt to stand for")

    return Command(name=name, prompt=prompt, help=help_text)
