"""How closely an automatic judgement matches what people decided."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MIN_PAIRS = 20
RELIABLE_AT = 0.9


class Trust(Enum):
    """Whether a judge can be relied on."""

    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Pair:
    """One case as the judge scored it and as a person did."""

    case_id: str
    judged: bool
    human: bool


@dataclass(frozen=True)
class Agreement:
    """How far the judge and the people agree, and which way it leans."""

    agreement: float
    trust: Trust
    bias: str
    too_generous: int
    too_harsh: int
    disagreements: tuple[str, ...]
    may_gate: bool
    reason: str = ""


def measure_agreement(pairs: list[Pair]) -> Agreement:
    """Measure how far the judge agrees with the people."""
    if not pairs:
        raise ValueError("there is nothing to compare")

    ids = [pair.case_id for pair in pairs]
    if len(ids) != len(set(ids)):
        raise ValueError("a case cannot be compared twice")

    agreed = [pair for pair in pairs if pair.judged == pair.human]
    too_generous = sum(1 for pair in pairs if pair.judged and not pair.human)
    too_harsh = sum(1 for pair in pairs if not pair.judged and pair.human)
    agreement = len(agreed) / len(pairs)

    if len(pairs) < MIN_PAIRS:
        trust = Trust.UNKNOWN
        reason = f"{MIN_PAIRS} comparisons are needed before trusting this judge"
    elif agreement >= RELIABLE_AT:
        trust, reason = Trust.RELIABLE, ""
    else:
        trust = Trust.UNRELIABLE
        reason = f"this judge agrees with people {agreement:.0%} of the time"

    return Agreement(
        agreement=agreement,
        trust=trust,
        bias="too generous"
        if too_generous > too_harsh
        else "too harsh"
        if too_harsh > too_generous
        else "",
        too_generous=too_generous,
        too_harsh=too_harsh,
        disagreements=tuple(
            pair.case_id for pair in pairs if pair.judged != pair.human
        ),
        may_gate=trust is Trust.RELIABLE,
        reason=reason,
    )
