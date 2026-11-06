"""Holding one tool to a rate and a number in flight."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from agent.src.security.rate_limit import Limit, RateLimiter
from agent.src.security.tool_call_check import Check, Preflight, check_call
from agent.src.security.tool_concurrency import ConcurrencyLimits, Gate


@dataclass
class ToolPace:
    """How fast, and how many at once, one tool may be called."""

    gate: Gate | None = None
    limiter: RateLimiter | None = None
    _now: Any = field(default=time.monotonic)

    @classmethod
    def from_config(cls, raw: Any) -> "ToolPace":
        """Build the pacing rules from a raw config section."""
        section = raw if isinstance(raw, dict) else {}

        gate = None
        concurrency = section.get("concurrency")
        if isinstance(concurrency, dict) and concurrency:
            gate = Gate(
                limits=ConcurrencyLimits(
                    per_tool=dict(concurrency.get("per_tool") or {}),
                    default=int(concurrency.get("default", 1)),
                )
            )

        limiter = None
        rate = section.get("rate")
        if isinstance(rate, dict) and rate:
            limiter = RateLimiter(
                Limit(
                    per_second=float(rate.get("per_second", 1)),
                    burst=int(rate.get("burst", 1)),
                )
            )

        return cls(gate=gate, limiter=limiter)

    def in_flight(self, tool: str) -> int:
        """How many calls to `tool` are in flight."""
        return self.gate.in_flight_for(tool) if self.gate else 0

    def may_call(self, tool: str, *, run: str) -> Check:
        """Whether this call may go now, as a preflight answer."""
        within_rate = True
        if self.limiter is not None:
            within_rate = self.limiter.check(tool, now=self._now()).allowed

        within_concurrency = True
        if self.gate is not None and within_rate:
            within_concurrency = self.gate.enter(tool, run=run).admitted

        return check_call(
            Preflight(
                tool=tool,
                within_rate_limit=within_rate,
                within_concurrency=within_concurrency,
                server_trusted=True,
                shape_unchanged=True,
                arguments_valid=True,
                credential_available=True,
                destination_allowed=True,
            )
        )

    def done(self, tool: str, *, run: str) -> None:
        """Release the slot `run` held for `tool`."""
        if self.gate is not None:
            self.gate.leave(tool, run=run)
