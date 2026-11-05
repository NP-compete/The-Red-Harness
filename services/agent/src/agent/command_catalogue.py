"""The commands this agent ships with, and how a typed line becomes a prompt."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from agent.src.agent.command_config import load_declared_commands
from agent.src.agent.commands import Command, CommandRegistry, Resolved
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

SHIPPED: list[Command] = [
    Command(
        name="summarise",
        prompt="Summarise the conversation so far{about}. Keep it to the points "
        "that would matter to someone picking this up cold.",
        help="Sum up this conversation",
    ),
    Command(
        name="explain",
        prompt="Explain your last answer{about} step by step, including what you "
        "read and what you inferred.",
        help="Explain the last answer in more detail",
    ),
    Command(
        name="sources",
        prompt="List the sources behind your last answer{about}, and say plainly "
        "which claims rest on nothing you read.",
        help="Show what the last answer rests on",
    ),
    Command(
        name="shorter",
        prompt="Say your last answer again{about}, shorter, keeping every fact.",
        help="Rewrite the last answer more briefly",
    ),
]


def _declared_path() -> Path:
    """Where this deployment's own commands are read from."""
    return Path(settings.COMMANDS_PATH)


@lru_cache(maxsize=1)
def declared() -> list[Command]:
    """What this deployment added, or nothing if it added nothing."""
    path = _declared_path()
    try:
        return load_declared_commands(path)
    except ValueError as error:
        logger.error("Commands declared in %s could not be read: %s", path, error)
        return []


def registry() -> CommandRegistry:
    """The command registry: shipped commands, overridden by declared ones."""
    return CommandRegistry(shipped=SHIPPED, declared=declared())


def expand(line: str) -> str:
    """Turn `/name argument` into the sentence it stands for."""
    resolved = registry().resolve(line.strip())
    if not isinstance(resolved, Resolved):
        return line

    about = f", about {resolved.argument}" if resolved.argument else ""
    return resolved.prompt.format(about=about)
