"""The commands a reader can type, as the composer sees them."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agent.src.agent.command_catalogue import registry

router = APIRouter(tags=["commands"])


class SlashCommandOut(BaseModel):
    """One slash command, name and help only."""

    name: str
    help: str = ""


class CommandsOut(BaseModel):
    """Every slash command this deployment offers."""

    commands: list[SlashCommandOut]


@router.get("/commands", responses={200: {"model": CommandsOut}})
async def list_commands() -> dict:
    """Name and help only."""
    return {
        "commands": [
            {"name": command.name, "help": command.help}
            for command in registry().palette()
        ]
    }
