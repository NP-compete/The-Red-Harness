"""Taking in a file of someone else's data."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

TOO_MALFORMED = 0.5


class Verdict(Enum):
    """Whether an imported batch is taken, held, or refused."""

    ACCEPT = "accept"
    HOLD = "hold"
    REFUSE = "refuse"


@dataclass(frozen=True)
class Batch:
    """An uploaded batch of rows, and everything checked about it."""

    rows: int
    rows_malformed: int
    declared_rows: int
    from_outside: bool
    contains_personal_data: bool
    consent_recorded: bool
    scanned: bool
    scan_clean: bool
    importer_may_import: bool

    def __post_init__(self) -> None:
        """Reject an empty batch, or more bad rows than rows."""
        if self.rows < 1:
            raise ValueError("there is nothing in this file")
        if self.rows_malformed > self.rows:
            raise ValueError("a file cannot hold more bad rows than rows")


@dataclass(frozen=True)
class Admitted:
    """How much of a batch was taken, and whether it is trusted."""

    verdict: Verdict
    reason: str
    rows_taken: int
    trusted: bool


def admit_import(batch: Batch) -> Admitted:
    """Decide how much of `batch` may be taken in."""
    trusted = not batch.from_outside
    taken = batch.rows - batch.rows_malformed

    def no(verdict: Verdict, reason: str) -> Admitted:
        """A refusal or hold with this reason, taking nothing."""
        return Admitted(verdict=verdict, reason=reason, rows_taken=0, trusted=trusted)

    if not batch.importer_may_import:
        return no(Verdict.REFUSE, "this person cannot import into this workspace")
    if not batch.scanned:
        return no(Verdict.REFUSE, "this file has not been scanned")
    if not batch.scan_clean:
        return no(Verdict.REFUSE, "the scan found something in this file")
    if batch.rows < batch.declared_rows:
        return no(Verdict.REFUSE, "this file is incomplete")
    if batch.rows_malformed / batch.rows > TOO_MALFORMED:
        return no(Verdict.REFUSE, "most of this file could not be read")
    if batch.contains_personal_data and not batch.consent_recorded:
        return no(Verdict.HOLD, "this holds personal data with no recorded consent")

    return Admitted(
        verdict=Verdict.ACCEPT, reason="", rows_taken=taken, trusted=trusted
    )
