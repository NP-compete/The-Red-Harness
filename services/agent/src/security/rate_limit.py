"""Holding each caller to an agreed rate, with room for a normal burst."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Limit:
    """A sustained rate and the burst allowed above it."""

    per_second: float
    burst: int

    def __post_init__(self) -> None:
        """Reject a limit that would let nothing through."""
        if self.per_second <= 0:
            raise ValueError("a rate of no calls per second allows nothing")
        if self.burst < 1:
            raise ValueError("a burst must allow at least one call")


@dataclass(frozen=True)
class Check:
    """Whether a call is allowed now, and what is left."""

    allowed: bool
    remaining: int
    retry_after: float = 0.0
    reason: str = ""


class RateLimiter:
    """A token bucket per key."""

    def __init__(self, limit: Limit) -> None:
        """Start with every key at a full bucket."""
        self._limit = limit
        self._state: dict[str, tuple[float, float]] = {}

    def check(self, key: str, *, now: float) -> Check:
        """Take a token for `key` if one is there, and say what is left."""
        tokens = self._refill(key, now=now)

        if tokens < 1:
            return Check(
                allowed=False,
                remaining=0,
                retry_after=(1 - tokens) / self._limit.per_second,
                reason=f"the limit is {self._limit.per_second:g} calls per second",
            )

        tokens -= 1
        self._state[key] = (tokens, max(now, self._state[key][1]))
        return Check(allowed=True, remaining=int(tokens))

    def peek(self, key: str, *, now: float) -> Check:
        """What `check` would say, without taking a token."""
        tokens = self._refill(key, now=now)
        return Check(allowed=tokens >= 1, remaining=int(tokens))

    def _refill(self, key: str, *, now: float) -> float:
        """The tokens `key` has at `now`, after refilling for elapsed time."""
        if not key.strip():
            raise ValueError("a rate limit needs something to count against")

        tokens, last = self._state.get(key, (float(self._limit.burst), now))
        elapsed = max(0.0, now - last)
        tokens = min(
            float(self._limit.burst), tokens + elapsed * self._limit.per_second
        )
        self._state[key] = (tokens, max(now, last))
        return tokens
