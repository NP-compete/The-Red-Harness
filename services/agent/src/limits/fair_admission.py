"""Who gets shed when the pod is full."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FairShare:
    """How much of the pod each active caller is holding."""

    capacity: int
    _held: dict[str, int] = field(default_factory=dict)

    @property
    def active_callers(self) -> int:
        """How many callers hold a slice."""
        return len(self._held)

    def held_by(self, caller: str) -> int:
        """How many slices `caller` holds."""
        return self._held.get(caller, 0)

    def may_start(self, caller: str) -> bool:
        """Whether this caller may take another slice."""
        if self.capacity <= 0:
            return True

        mine = self.held_by(caller)
        if mine >= self.capacity:
            return False

        claimants = self.active_callers + (0 if caller in self._held else 1)

        share = max(self.capacity // claimants, 1)
        return mine < share

    def took(self, caller: str) -> None:
        """Record that `caller` took a slice."""
        self._held[caller] = self.held_by(caller) + 1

    def finished(self, caller: str) -> None:
        """Give the slice back. Harmless if it was never taken."""
        left = self.held_by(caller) - 1
        if left > 0:
            self._held[caller] = left
        else:
            self._held.pop(caller, None)
