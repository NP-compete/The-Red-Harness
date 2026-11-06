"""Checking the figures in an answer against the figures that were read."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class NumericCheck:
    """How many figures were checked, and which were unsupported."""

    checked: int
    unsupported: list[str]

    @property
    def trustworthy(self) -> bool:
        """Whether every figure in the answer was supported."""
        return not self.unsupported


def _value(text: str) -> Decimal | None:
    """`text` as a number, or `None` if it is not one."""
    try:
        return Decimal(text.replace(",", "")).normalize()
    except InvalidOperation:
        return None


def check_numbers(answer: str, *, read: list[str]) -> NumericCheck:
    """Check every figure in `answer` against what was `read`."""
    if not read:
        raise ValueError("there is nothing to check the answer against")

    found = {
        value
        for source in read
        for text in _NUMBER.findall(source)
        if (value := _value(text))
    }

    seen: dict[Decimal, str] = {}
    for text in _NUMBER.findall(answer):
        value = _value(text)
        if value is not None and value not in seen:
            seen[value] = text

    return NumericCheck(
        checked=len(seen),
        unsupported=[text for value, text in seen.items() if value not in found],
    )
