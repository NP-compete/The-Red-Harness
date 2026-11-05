"""Checking an answer is the shape that was asked for."""

from __future__ import annotations

from dataclasses import dataclass

KINDS = {"text", "list", "number"}


@dataclass(frozen=True)
class Field:
    """One field an answer must carry, and the shape it must take."""

    name: str
    kind: str
    required: bool
    max_words: int | None

    def __post_init__(self) -> None:
        """Reject an unknown kind or a word limit of none."""
        if self.kind not in KINDS:
            raise ValueError(f"{self.kind} is not a kind of field")
        if self.max_words is not None and self.max_words < 1:
            raise ValueError("a limit of no words leaves nothing to say")


@dataclass(frozen=True)
class Contract:
    """The shape an answer has to take."""

    fields: tuple[Field, ...]

    def __post_init__(self) -> None:
        """Reject a contract that asks for nothing."""
        if not self.fields:
            raise ValueError("a contract must ask for something")


@dataclass(frozen=True)
class Check:
    """How an answer measured up to its contract."""

    fits: bool
    missing: tuple[str, ...]
    wrong_shape: tuple[str, ...]
    too_long: tuple[str, ...]
    unexpected: tuple[str, ...]
    detail: str = ""


def check_output(answer: dict[str, object], *, contract: Contract) -> Check:
    """Check `answer` against `contract`."""
    missing: list[str] = []
    wrong_shape: list[str] = []
    too_long: list[str] = []

    for field in contract.fields:
        value = answer.get(field.name)

        if field.name not in answer or _is_blank(value):
            if field.required:
                missing.append(field.name)
            continue

        if not _right_shape(value, field.kind):
            wrong_shape.append(field.name)
            continue

        if field.max_words is not None and _words(value) > field.max_words:
            too_long.append(field.name)

    unexpected = tuple(sorted(set(answer) - {field.name for field in contract.fields}))

    notes = [
        f"{label}: {', '.join(names)}"
        for label, names in (
            ("missing", missing),
            ("wrong shape", wrong_shape),
            ("too long", too_long),
        )
        if names
    ]

    return Check(
        fits=not (missing or wrong_shape or too_long),
        missing=tuple(missing),
        wrong_shape=tuple(wrong_shape),
        too_long=tuple(too_long),
        unexpected=unexpected,
        detail="; ".join(notes),
    )


def _is_blank(value: object) -> bool:
    """Whether a value is missing or empty."""
    return value is None or (isinstance(value, str) and not value.strip())


def _right_shape(value: object, kind: str) -> bool:
    """Whether `value` has the shape `kind` calls for."""
    if kind == "text":
        return isinstance(value, str)
    if kind == "list":
        return isinstance(value, list)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _words(value: object) -> int:
    """How many words a value amounts to."""
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, list):
        return sum(len(str(item).split()) for item in value)
    return 0
