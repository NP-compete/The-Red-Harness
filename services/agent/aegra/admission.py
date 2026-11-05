"""Bound the number of runs a pod will start at once."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent.src.limits.fair_admission import FairShare
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_RUN_PATH = re.compile(r"^/(?:threads/[^/]+/)?runs(?:/(?:stream|wait))?/?$")


def _caller_of(request: Request) -> str:
    """Who to charge this slice to, cheaply."""
    from agent.aegra.auth import _decode_sub_unverified

    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        return ""
    return _decode_sub_unverified(header[7:]) or ""


class AdmissionControlMiddleware(BaseHTTPMiddleware):
    """Reject new runs past a concurrency limit instead of queueing them."""

    def __init__(self, app: Any, max_concurrent: int) -> None:
        """Gate run starts at ``max_concurrent``; zero disables the gate."""
        super().__init__(app)
        self.max_concurrent = max_concurrent
        self._sem = asyncio.Semaphore(max_concurrent) if max_concurrent > 0 else None
        self._share = FairShare(capacity=max_concurrent)
        if self._sem is not None:
            logger.info("Admission control: max %d concurrent runs", max_concurrent)

    def _gated(self, request: Request) -> bool:
        return request.method == "POST" and bool(_RUN_PATH.match(request.url.path))

    def _closed_for(self, request: Request) -> Any:
        """A refusal when this pod should not be starting work, else None."""
        from agent.aegra.shutdown import is_shutting_down

        if is_shutting_down():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": (
                        "This agent is shutting down and is not starting "
                        "new runs. Your request was not begun."
                    ),
                    "error_type": "shutting_down",
                },
            )

        return None

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Admit the request, or shed it with 503 when at capacity."""
        if not self._gated(request):
            return await call_next(request)

        refusal = self._closed_for(request)
        if refusal is not None:
            return refusal

        if self._sem is None:
            return await call_next(request)

        if self._sem.locked():
            logger.warning(
                "Shedding run: %d concurrent runs already in flight",
                self.max_concurrent,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
                content={
                    "detail": (
                        "The agent is at capacity. Please retry in a few seconds."
                    ),
                    "error_type": "at_capacity",
                },
            )

        caller = _caller_of(request)
        if not self._share.may_start(caller):
            logger.warning(
                "Shedding a run for %s: already holding %d of %d",
                caller or "an unnamed caller",
                self._share.held_by(caller),
                self.max_concurrent,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
                content={
                    "detail": (
                        "You already have as much of this agent as anyone "
                        "else waiting. Please retry in a few seconds."
                    ),
                    "error_type": "fair_share",
                },
            )

        await self._sem.acquire()
        self._share.took(caller)
        released = False

        def _give_back() -> None:
            self._share.finished(caller)

        try:
            response = await call_next(request)
        except BaseException:
            self._sem.release()
            _give_back()
            raise

        iterator = getattr(response, "body_iterator", None)
        if iterator is None:
            self._sem.release()
            _give_back()
            return response

        sem = self._sem

        async def _release_when_done() -> Any:
            nonlocal released
            try:
                async for chunk in iterator:
                    yield chunk
            finally:
                if not released:
                    released = True
                    sem.release()
                    _give_back()

        response.body_iterator = _release_when_done()
        return response
