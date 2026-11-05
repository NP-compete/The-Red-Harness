"""Holding an inbound caller to its own limits at the door."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent.aegra.admission import _RUN_PATH
from agent.src.security.inbound_limits import Limits, admit
from agent.src.security.rate_limit import Limit, RateLimiter
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _thread_of(request: Any) -> str:
    """Which conversation this run is for, if it names one."""
    parts = [p for p in str(request.url.path).split("/") if p]
    return parts[1] if len(parts) > 2 and parts[0] == "threads" else ""


async def caller_of(request: Any) -> str:
    """The verified identity of whoever is calling, or nothing."""
    from agent.aegra import auth_helpers

    try:
        found = await auth_helpers.memory_user_id(request)
    except Exception:
        return ""

    return "" if found == "anonymous" else str(found or "")


async def spent_by(caller: str) -> Decimal:
    """What `caller` has spent today."""
    from agent.src.security.caller_spend import spent_today

    return await spent_today(caller)


async def claim_thread(thread: str, subject: str) -> Any:
    """Take the conversation for this run, or say who has it."""
    from agent.src.security.shared_thread_lease import SharedThreadLeases

    return await SharedThreadLeases().claim(thread=thread, subject=subject)


async def release_thread(thread: str, subject: str) -> None:
    """Release `subject`'s lease on `thread`."""
    from agent.src.security.shared_thread_lease import SharedThreadLeases

    await SharedThreadLeases().release(thread=thread, subject=subject)


async def team_spend(team: str) -> Decimal:
    """What `team` has spent today."""
    from agent.src.security.caller_spend import spent_today

    return await spent_today(f"team:{team}")


def configured_allowance() -> Any:
    """What one person, and one team, may spend in a day."""
    from agent.src.agent.config import agent_config

    try:
        return agent_config.get_limits_config()
    except Exception as error:
        logger.warning("Could not read the spending allowance: %s", error)
        from agent.src.limits.fair_share import Allowance

        return Allowance(per_person=None, per_team=None)


async def teams_with_a_budget(request: Any) -> tuple[str, ...]:
    """Which of the budgeted teams this caller is in."""
    from agent.aegra.auth_helpers import memory_user_id
    from agent.src.ldap import resolve_user_groups

    allowance = configured_allowance()
    if not allowance.teams:
        return ()
    try:
        who = await memory_user_id(request)
        return tuple(await resolve_user_groups(who, allowance.teams))
    except Exception:
        return ()


def configured_limits() -> Limits | None:
    """The configured inbound limits, or `None` if they cannot be read."""
    from agent.src.agent.config import agent_config

    try:
        found: Limits | None = agent_config.get_inbound_config().limits
        return found
    except Exception as error:
        logger.warning("Could not read inbound limits: %s", error)
        return None


class InboundLimitMiddleware(BaseHTTPMiddleware):
    """Holds inbound runs to the configured rate, spend and lease limits."""

    def __init__(
        self,
        app: Any,
        *,
        limits: Callable[[], Limits | None] = configured_limits,
        caller_of: Callable[[Any], Awaitable[str]] = caller_of,
        spent_by: Callable[[str], Awaitable[Decimal]] = spent_by,
        allowance: Callable[[], Any] = configured_allowance,
        team_spend: Callable[[str], Awaitable[Decimal]] = team_spend,
        teams_of: Callable[[Any], Any] = teams_with_a_budget,
        claim_thread: Callable[[str, str], Any] = claim_thread,
        release_thread: Callable[[str, str], Any] = release_thread,
    ) -> None:
        """Wire the middleware to its limit, spend and lease sources."""
        super().__init__(app)
        self._limits = limits
        self._caller_of = caller_of
        self._spent_by = spent_by
        self._allowance = allowance
        self._team_spend = team_spend
        self._teams_of = teams_of
        self._claim_thread = claim_thread
        self._release_thread = release_thread
        self._limiters: dict[tuple[float, int], RateLimiter] = {}

    def _gated(self, request: Request) -> bool:
        """Whether this request is one of the run starts that is limited."""
        return request.method == "POST" and bool(_RUN_PATH.match(request.url.path))

    def _limiter(self, limits: Limits) -> RateLimiter:
        """The rate limiter for these limits, made once and reused."""
        key = (limits.per_second, limits.burst)
        if key not in self._limiters:
            self._limiters[key] = RateLimiter(
                Limit(per_second=limits.per_second, burst=limits.burst)
            )
        return self._limiters[key]

    async def _over_budget(self, request: Request, caller: str) -> str | None:
        """Whether this run would exceed an allowance, and which."""
        from agent.src.limits.fair_share import OverBudget, check_within_budget

        allowance = self._allowance()
        if allowance.per_person is None and allowance.per_team is None:
            return None

        try:
            spent = await self._spent_by(caller)
        except Exception as error:
            logger.warning("Could not read today's spend for %s: %s", caller, error)
            return None

        theirs = Decimal("0")
        if allowance.per_team is not None:
            try:
                teams = await self._teams_of(request)
                if teams:
                    theirs = await self._team_spend(teams[0])
            except Exception as error:
                logger.warning("Could not read team spend: %s", error)

        try:
            check_within_budget(
                allowance=allowance, spent_by_person=spent, spent_by_team=theirs
            )
        except OverBudget as refused:
            return str(refused)
        return None

    async def _run_holding(
        self, thread: str, caller: str, request: Any, call_next: Any
    ) -> Any:
        """Run with the conversation held, and give it back after."""
        try:
            return await call_next(request)
        finally:
            if thread:
                await self._release_thread(thread, caller)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Apply the inbound limits, then pass the request on."""
        limits = self._limits()
        gated = self._gated(request)
        if not gated:
            return await call_next(request)

        caller = await self._caller_of(request)

        over = await self._over_budget(request, caller)
        if over is not None:
            logger.warning(
                "Refusing a run for %s: %s", caller or "an unnamed caller", over
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "3600"},
                content={"detail": over, "error_type": "over_budget"},
            )

        thread = _thread_of(request)
        if thread:
            held = await self._claim_thread(thread, caller)
            if not held.granted:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "detail": (
                            f"{held.held_by} is already running this "
                            f"conversation. Wait for it to finish, or start "
                            f"a new conversation."
                        ),
                        "error_type": "thread_busy",
                    },
                )

        if limits is None:
            return await self._run_holding(thread, caller, request, call_next)

        try:
            spent = await self._spent_by(caller) if caller else Decimal("0")
        except Exception as error:
            logger.warning("Could not read spend for %s: %s", caller, error)
            spent = Decimal("0")

        checked = self._limiter(limits).check(caller or "-", now=time.monotonic())
        found = admit(
            caller,
            limits=limits,
            rate_ok=checked.allowed,
            spent=spent,
            retry_after=checked.retry_after,
        )
        if found.allowed:
            return await self._run_holding(thread, caller, request, call_next)

        logger.warning(
            "Refusing a run for %s: %s", caller or "an unnamed caller", found.reason
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(max(1, int(found.retry_after)))},
            content={"detail": found.reason, "error_type": "caller_limit"},
        )
