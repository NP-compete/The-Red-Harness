"""Move a configuration tree forward one version."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from agent.src.agent.config.schema_version import (  # noqa: E402
    CURRENT,
    OLDEST_SUPPORTED,
)

AGENT_FILES = ("runtime/agent.yaml", "agent.yaml")


@dataclass(frozen=True)
class Move:
    """A key that changed name and nothing else."""

    frm: str
    to: str
    in_section: str = ""


MOVES: tuple[Move, ...] = ()
DECISIONS: tuple[str, ...] = ()


@dataclass
class Migration:
    """What a migration changed, refused, and left for a person to decide."""

    changed: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    decide: list[str] = field(default_factory=list)


_VERSION = re.compile(r"^(\s*)schema_version\s*:\s*(\S+)\s*$")


def _agent_file(tree: Path) -> Path | None:
    """The agent file in `tree`, or `None` if there is none."""
    for rel in AGENT_FILES:
        if (tree / rel).is_file():
            return tree / rel
    return None


def _declared(lines: list[str]) -> int | None:
    """The schema version declared in `lines`, if any."""
    for line in lines:
        found = _VERSION.match(line)
        if found:
            try:
                return int(found.group(2))
            except ValueError:
                return None
    return None


def _set_version(lines: list[str], version: int) -> list[str]:
    """`lines` with the schema version set to `version`."""
    for i, line in enumerate(lines):
        if _VERSION.match(line):
            lines[i] = f"schema_version: {version}\n"
            return lines
    return [f"schema_version: {version}\n"] + lines


def _rename(lines: list[str], move: Move) -> tuple[list[str], bool]:
    """Rewrite a key, leaving its value, indentation and comments."""
    pattern = re.compile(rf"^(\s*){re.escape(move.frm)}(\s*:.*)$")
    touched = False
    for i, line in enumerate(lines):
        found = pattern.match(line)
        if found:
            lines[i] = f"{found.group(1)}{move.to}{found.group(2)}\n"
            touched = True
    return lines, touched


def migrate(
    tree: Path,
    *,
    moves: tuple[Move, ...] = MOVES,
    decisions: tuple[str, ...] = DECISIONS,
    write: bool = True,
) -> Migration:
    """Take one tree forward one version, or say why not."""
    found = Migration()

    path = _agent_file(tree)
    if path is None:
        found.refused.append(f"{tree}: no agent.yaml, at either path")
        return found

    lines = path.read_text().splitlines(keepends=True)
    declared = _declared(lines)
    was = OLDEST_SUPPORTED if declared is None else declared

    if was >= CURRENT:
        found.refused.append(f"{path}: already at version {was}; nothing to do")
        return found

    lines = _set_version(lines, was + 1)
    found.changed.append(f"{path}: schema_version {was} -> {was + 1}")

    for move in moves:
        lines, touched = _rename(lines, move)
        if touched:
            found.changed.append(f"{path}: {move.frm} -> {move.to}")

    found.decide.extend(decisions)

    if write:
        path.write_text("".join(lines))
    return found


def main(argv: list[str] | None = None) -> int:
    """Migrate a config tree to the current schema version."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: migrate_config.py <tree> [--dry-run]", file=sys.stderr)
        return 2

    dry = "--dry-run" in args
    paths = [a for a in args if not a.startswith("-")]
    tree = Path(paths[0]).expanduser()

    found = migrate(tree, write=not dry)

    for line in found.changed:
        print(("would change  " if dry else "changed  ") + line)
    for line in found.refused:
        print(f"refused  {line}", file=sys.stderr)
    if found.decide:
        print("\nNot done for you — decide and edit:")
        for line in found.decide:
            print(f"  - {line}")

    return 1 if found.refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
