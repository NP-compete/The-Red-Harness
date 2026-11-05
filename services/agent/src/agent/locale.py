"""Choosing the language, zone and units a reply is written in."""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Signals:
    """Everything that bears on which locale to use."""

    chosen_language: str
    chosen_zone: str
    chosen_units: str
    language_written_in: str
    workspace_language: str
    workspace_zone: str
    workspace_units: str
    device_zone: str

    def __post_init__(self) -> None:
        """Reject a workspace with no language to fall back to."""
        if not self.workspace_language.strip():
            raise ValueError("a workspace needs a language to fall back to")


@dataclass(frozen=True)
class Locale:
    """The language, zone and units chosen, and where they came from."""

    language: str
    zone: str
    units: str
    language_from: str
    switched: bool


def _known(zone: str) -> bool:
    """Whether `zone` is a time zone this machine knows."""
    if not zone:
        return False
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def choose_locale(signals: Signals) -> Locale:
    """Choose the locale to answer in, given `signals`."""
    if signals.chosen_language:
        language, language_from = signals.chosen_language, "setting"
    elif (
        signals.language_written_in
        and signals.language_written_in != signals.workspace_language
    ):
        language, language_from = signals.language_written_in, "message"
    else:
        language, language_from = signals.workspace_language, "workspace"

    zone = next(
        (
            candidate
            for candidate in (
                signals.chosen_zone,
                signals.device_zone,
                signals.workspace_zone,
            )
            if _known(candidate)
        ),
        "UTC",
    )

    return Locale(
        language=language,
        zone=zone,
        units=signals.chosen_units or signals.workspace_units,
        language_from=language_from,
        switched=language != signals.workspace_language,
    )
