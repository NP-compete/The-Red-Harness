"""Telling whether a tool is still the tool that was approved."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


class Change(Enum):
    """One way a tool's shape can differ from the approved one."""

    PARAMETER_ADDED = "parameter-added"
    PARAMETER_REMOVED = "parameter-removed"
    PARAMETER_RETYPED = "parameter-retyped"
    REQUIREMENT_CHANGED = "requirement-changed"
    DESCRIPTION_CHANGED = "description-changed"
    SERVER_CHANGED = "server-changed"


WIDENING = {
    Change.PARAMETER_ADDED,
    Change.PARAMETER_RETYPED,
    Change.DESCRIPTION_CHANGED,
    Change.SERVER_CHANGED,
}


@dataclass(frozen=True)
class ToolShape:
    """The part of a tool's definition that approval was given against."""

    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    server: str = ""

    def __post_init__(self) -> None:
        """Reject a tool with no name."""
        if not self.name.strip():
            raise ValueError("a tool must have a name")


@dataclass(frozen=True)
class Comparison:
    """How a tool's current shape differs from its approved one."""

    changes: tuple[Change, ...]
    needs_reapproval: bool
    summary: str


def fingerprint(shape: ToolShape) -> str:
    """A stable hash of everything about `shape` that approval covered."""
    canonical = json.dumps(
        {
            "name": shape.name,
            "description": shape.description,
            "parameters": dict(sorted(shape.parameters.items())),
            "required": sorted(shape.required),
            "server": shape.server,
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def compare(approved: ToolShape, current: ToolShape) -> Comparison:
    """Describe how `current` differs from `approved`."""
    if approved.name != current.name:
        raise ValueError("two different tools cannot be compared")

    added = sorted(set(current.parameters) - set(approved.parameters))
    removed = sorted(set(approved.parameters) - set(current.parameters))
    retyped = sorted(
        name
        for name in set(approved.parameters) & set(current.parameters)
        if approved.parameters[name] != current.parameters[name]
    )

    changes: list[Change] = []
    notes: list[str] = []

    if added:
        changes.append(Change.PARAMETER_ADDED)
        notes.append(f"gained {', '.join(added)}")
    if removed:
        changes.append(Change.PARAMETER_REMOVED)
        notes.append(f"lost {', '.join(removed)}")
    if retyped:
        changes.append(Change.PARAMETER_RETYPED)
        notes.append(f"changed the type of {', '.join(retyped)}")
    if set(approved.required) != set(current.required):
        changes.append(Change.REQUIREMENT_CHANGED)
        notes.append("changed which arguments are required")
    if approved.description != current.description:
        changes.append(Change.DESCRIPTION_CHANGED)
        notes.append("was described differently")
    if approved.server != current.server:
        changes.append(Change.SERVER_CHANGED)
        notes.append(f"moved from {approved.server} to {current.server}")

    return Comparison(
        changes=tuple(changes),
        needs_reapproval=any(change in WIDENING for change in changes),
        summary=f"{approved.name} {'; '.join(notes)}" if notes else "",
    )


def shape_of(tool: object) -> ToolShape:
    """The shape of a tool as it is described right now."""
    parameters: dict[str, str] = {}
    required: list[str] = []

    schema = getattr(tool, "args_schema", None)
    fields = getattr(schema, "model_fields", None)
    if isinstance(fields, dict):
        for name, field in fields.items():
            parameters[str(name)] = getattr(
                getattr(field, "annotation", None), "__name__", "?"
            )
            if getattr(field, "is_required", lambda: False)():
                required.append(str(name))

    return ToolShape(
        name=str(getattr(tool, "name", "") or "?"),
        description=str(getattr(tool, "description", "") or ""),
        parameters=parameters,
        required=tuple(sorted(required)),
    )


class ShapeMemory:
    """The shape each tool had when this run first saw it."""

    def __init__(self) -> None:
        """Start with no tool shapes remembered."""
        self._seen: dict[str, ToolShape] = {}

    def check(self, current: ToolShape) -> tuple[bool, str]:
        """Whether `current` still matches what was approved, and why not."""
        approved = self._seen.get(current.name)
        if approved is None:
            self._seen[current.name] = current
            return True, ""

        found = compare(approved, current)
        if found.needs_reapproval:
            return False, found.summary

        if found.changes:
            self._seen[current.name] = current
        return True, ""
