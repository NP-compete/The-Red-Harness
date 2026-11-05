"""Recording what happened without flooding the metrics with labels."""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_LABEL_LENGTH = 40
OTHER = "other"


@dataclass(frozen=True)
class Measurement:
    """One measurement, its value and its labels."""

    name: str
    value: float
    labels: dict[str, str]

    def __post_init__(self) -> None:
        """Reject a nameless measurement, a non-finite value, or a bad label."""
        if not self.name.strip():
            raise ValueError("a measurement must have a name")
        if not math.isfinite(self.value):
            raise ValueError("a measurement must be a real number")
        for key, value in self.labels.items():
            if " " in value or len(value) > MAX_LABEL_LENGTH:
                raise ValueError(f"{key} looks like free text, not a label")


@dataclass(frozen=True)
class Prepared:
    """The measurements as they will be recorded, and what was dropped."""

    measurements: tuple[Measurement, ...]
    dropped_labels: tuple[str, ...]
    collapsed_labels: tuple[str, ...]
    series: int
    capped: bool


def prepare(
    measurements: list[Measurement],
    *,
    known_labels: tuple[str, ...],
    max_values: int = 50,
    max_series: int = 1000,
) -> Prepared:
    """Prepare `measurements` for recording, dropping unknown labels."""
    if not measurements:
        raise ValueError("there is nothing to record")

    allowed = set(known_labels)
    dropped = sorted(
        {key for item in measurements for key in item.labels if key not in allowed}
    )

    trimmed = [
        Measurement(
            name=item.name,
            value=item.value,
            labels={k: v for k, v in item.labels.items() if k in allowed},
        )
        for item in measurements
    ]

    seen: dict[str, set[str]] = {}
    for item in trimmed:
        for key, value in item.labels.items():
            seen.setdefault(key, set()).add(value)
    collapsed = tuple(
        sorted(key for key, values in seen.items() if len(values) > max_values)
    )

    if collapsed:
        trimmed = [
            Measurement(
                name=item.name,
                value=item.value,
                labels={
                    key: (OTHER if key in collapsed else value)
                    for key, value in item.labels.items()
                },
            )
            for item in trimmed
        ]

    kept, keys = _cap(trimmed, max_series=max_series)

    return Prepared(
        measurements=tuple(kept),
        dropped_labels=tuple(dropped),
        collapsed_labels=collapsed,
        series=len(keys),
        capped=len(kept) < len(trimmed),
    )


def _cap(
    measurements: list[Measurement], *, max_series: int
) -> tuple[list[Measurement], set[tuple[tuple[str, str], ...]]]:
    """The measurements kept within `max_series`, and the keys collapsed."""
    keys: set[tuple[tuple[str, str], ...]] = set()
    kept: list[Measurement] = []

    for item in measurements:
        key = tuple(sorted(item.labels.items()))
        if key not in keys and len(keys) >= max_series:
            continue
        keys.add(key)
        kept.append(item)

    return kept, keys
