"""Commands a person can type into a conversation."""

from __future__ import annotations

from dataclasses import dataclass

_RESERVED = frozenset({"approve", "allow", "bypass", "deny"})


@dataclass(frozen=True)
class Command:
    """One slash command: its name, the prompt it expands to, and its help."""

    name: str
    prompt: str
    help: str

    def __post_init__(self) -> None:
        """Reject a command that takes a reserved name."""
        if self.name in _RESERVED:
            raise ValueError(f"'{self.name}' is reserved")


@dataclass(frozen=True)
class Resolved:
    """A command matched from an input line, with its argument."""

    command: Command
    argument: str

    @property
    def prompt(self) -> str:
        """The prompt the matched command expands to."""
        return self.command.prompt


@dataclass(frozen=True)
class Unknown:
    """An input line that looked like a command but matched nothing."""

    name: str


class CommandRegistry:
    """The slash commands available, shipped ones overridden by declared ones."""

    def __init__(self, shipped: list[Command], declared: list[Command]) -> None:
        """Index shipped commands, then let declared commands override them."""
        self._commands = {c.name: c for c in shipped}
        self._commands.update({c.name: c for c in declared})

    def palette(self) -> list[Command]:
        """Every available command, sorted by name."""
        return sorted(self._commands.values(), key=lambda c: c.name)

    def resolve(self, line: str) -> Resolved | Unknown | None:
        """Match `line` to a command, or `None` if it is not a command at all."""
        if not line.startswith("/"):
            return None

        name, _, argument = line[1:].partition(" ")
        command = self._commands.get(name)
        if command is None:
            return Unknown(name=name)
        return Resolved(command=command, argument=argument.strip())
