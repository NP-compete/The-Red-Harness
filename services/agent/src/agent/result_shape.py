"""Working out how a tool's result is best shown."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

PAGE_AFTER_ROWS = 100
COLLAPSE_AFTER_WORDS = 500

SCALARS = (str, int, float, bool, type(None))
_PYTHON_HINTS = ("def ", "import ", "class ", "lambda ")
_CODE_HINTS = (*_PYTHON_HINTS, "function ", "=>", ";\n", "{\n", "#!/")


class Shape(Enum):
    """The shape a tool result takes."""

    TABLE = "table"
    FIELDS = "fields"
    LIST = "list"
    TEXT = "text"
    CODE = "code"
    JSON = "json"
    EMPTY = "empty"


@dataclass(frozen=True)
class Described:
    """What a result looks like, and how it should be shown."""

    shape: Shape
    rows: int = 0
    columns: tuple[str, ...] = ()
    language: str = ""
    needs_paging: bool = False
    needs_collapsing: bool = False


def describe_result(result: object) -> Described:
    """Describe the shape of `result`."""
    if isinstance(result, str):
        return _describe_text(result)
    if isinstance(result, list):
        return _describe_list(result)
    if isinstance(result, dict):
        return _describe_dict(result)
    if isinstance(result, SCALARS):
        return Described(Shape.TEXT)
    raise ValueError("this result cannot be shown")


def _describe_text(text: str) -> Described:
    """Describe a string result."""
    if not text.strip():
        return Described(Shape.EMPTY)

    words = len(text.split())
    if any(hint in text for hint in _CODE_HINTS):
        language = "python" if any(hint in text for hint in _PYTHON_HINTS) else ""
        return Described(
            Shape.CODE, language=language, needs_collapsing=words > COLLAPSE_AFTER_WORDS
        )

    return Described(Shape.TEXT, needs_collapsing=words > COLLAPSE_AFTER_WORDS)


def _describe_list(items: list) -> Described:
    """Describe a list result."""
    if not items:
        return Described(Shape.EMPTY)

    if all(isinstance(item, dict) for item in items):
        keys = {frozenset(item) for item in items}
        if len(keys) == 1:
            columns = tuple(sorted(next(iter(keys))))
            return Described(
                Shape.TABLE,
                rows=len(items),
                columns=columns,
                needs_paging=len(items) > PAGE_AFTER_ROWS,
            )
        return Described(Shape.JSON, rows=len(items))

    return Described(Shape.LIST, rows=len(items))


def _describe_dict(fields: dict) -> Described:
    """Describe a mapping result."""
    if not fields:
        return Described(Shape.EMPTY)

    if all(isinstance(value, SCALARS) for value in fields.values()):
        return Described(Shape.FIELDS, columns=tuple(sorted(fields)))

    return Described(Shape.JSON)
