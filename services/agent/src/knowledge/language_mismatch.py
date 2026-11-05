"""Reading material written in a language other than the question."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

CONFIDENT = 0.5


class Handling(Enum):
    """What to do with a passage in another language."""

    AS_IS = "as_is"
    TRANSLATE = "translate"
    UNTRANSLATED = "untranslated"


@dataclass(frozen=True)
class Found:
    """One retrieved chunk and the language it appears to be in."""

    chunk: str
    language: str
    confidence: float
    translatable: bool

    def __post_init__(self) -> None:
        """Reject a confidence outside zero to one."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("a confidence runs from zero to one")


@dataclass(frozen=True)
class Step:
    """What to do with one chunk when reading the results."""

    chunk: str
    language: str
    handling: Handling
    language_uncertain: bool


def _base(language: str) -> str:
    """The base language tag, without its region."""
    return language.split("-")[0].lower()


def plan_reading(results: list[Found], *, asked_in: str) -> list[Step]:
    """Plan how to read `results` for a question asked in `asked_in`."""
    if not asked_in.strip():
        raise ValueError("a question needs a language to compare against")

    wanted = _base(asked_in)

    plan = []
    for result in results:
        uncertain = result.confidence < CONFIDENT
        if uncertain or _base(result.language) == wanted:
            handling = Handling.AS_IS
        elif result.translatable:
            handling = Handling.TRANSLATE
        else:
            handling = Handling.UNTRANSLATED
        plan.append(
            Step(
                chunk=result.chunk,
                language=result.language,
                handling=handling,
                language_uncertain=uncertain,
            )
        )
    return plan
