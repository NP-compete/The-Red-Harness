"""Finding a configuration key that nothing reads."""

from __future__ import annotations

import typing
from typing import Any

from pydantic import BaseModel


def _models_in(annotation: Any) -> list[type[BaseModel]]:
    """Every model this annotation could hold, through unions and lists."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]

    origin = typing.get_origin(annotation)
    if origin is dict:
        return []
    if origin is None:
        return []

    found: list[type[BaseModel]] = []
    for arg in typing.get_args(annotation):
        found.extend(_models_in(arg))
    return found


def unknown_keys(data: Any, model: type[BaseModel], path: str = "") -> list[str]:
    """Every key in `data` that `model` has no field for."""
    if not isinstance(data, dict):
        return []

    fields = model.model_fields
    found: list[str] = []

    for key, value in data.items():
        here = f"{path}.{key}" if path else str(key)
        field = fields.get(str(key))
        if field is None:
            found.append(
                f"'{here}' is not a setting anything reads — "
                "check the spelling, or remove it"
            )
            continue

        for nested in _models_in(field.annotation):
            if isinstance(value, dict):
                found.extend(unknown_keys(value, nested, here))
            elif isinstance(value, list):
                for item in value:
                    found.extend(unknown_keys(item, nested, here))

    return found
