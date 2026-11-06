"""Recording what somebody decided about a paused run (CLI-6, E28-T5)."""

from __future__ import annotations

import json
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

MAX_DECISIONS = 20

MAX_BODY = 256 * 1024


def decisions_in(body: bytes) -> list[dict[str, Any]] | None:
    """The decisions a resume carries, or `None` if it is not one."""
    if not body or len(body) > MAX_BODY:
        return None
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    command = payload.get("command")
    if not isinstance(command, dict):
        return None
    resume = command.get("resume")
    if resume is None:
        return None

    found = resume.get("decisions") if isinstance(resume, dict) else None
    if isinstance(found, list):
        return [one for one in found if isinstance(one, dict)][:MAX_DECISIONS]
    return []


def summarise(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise the approval decisions in a run request."""
    kinds = [str(one.get("type") or "unknown") for one in decisions]
    return {
        "decisions": kinds,
        "count": len(kinds),
        "explained": any(bool(one.get("message")) for one in decisions),
    }


async def record(request: Any, body: bytes) -> None:
    """Write one line for a decision, or nothing at all."""
    found = decisions_in(body)
    if found is None:
        return

    try:
        from agent.aegra.auth_helpers import authenticated_user_id
        from agent.src.audit import emit_audit_event
        from agent.src.audit.events import AuditEventType

        try:
            who = await authenticated_user_id(request, reject_anonymous=False)
        except Exception:  # noqa: BLE001 - an unreadable identity is not fatal
            who = ""

        emit_audit_event(
            AuditEventType.APPROVAL_DECIDED,
            thread=_thread_of(request),
            user=who or "unknown",
            **summarise(found),
        )
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not record an approval decision: %s", error)


def _thread_of(request: Any) -> str:
    """The thread id in a request path, or an empty string."""
    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    parts = [part for part in path.split("/") if part]
    if "threads" in parts:
        index = parts.index("threads")
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


class ApprovalAuditMiddleware:
    """Pure ASGI, so the body can be replayed rather than eaten."""

    def __init__(self, app: Any) -> None:
        """Wrap `app`."""
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Record the approval decisions on run requests, then pass them on."""
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path") or "")
        if "/runs" not in path or "/threads/" not in path:
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        held = 0
        more = True
        while more:
            message = await receive()
            if message["type"] != "http.request":
                await self.app(scope, _replay(chunks, receive), send)
                return
            piece = message.get("body") or b""
            chunks.append(piece)
            held += len(piece)
            more = message.get("more_body", False)
            if held > MAX_BODY and more:
                await self.app(scope, _replay(chunks, receive, keep_reading=True), send)
                return

        body = b"".join(chunks)
        try:
            from starlette.requests import Request

            await record(Request(scope), body)
        except Exception as error:  # noqa: BLE001
            logger.warning("Could not record an approval decision: %s", error)

        await self.app(scope, _replay([body], receive), send)


def _replay(chunks: list[bytes], original: Any, *, keep_reading: bool = False) -> Any:
    """Give the application the body it would have received."""
    sent = {"done": False}

    async def receive() -> dict[str, Any]:
        """Replay the body that was already read."""
        if not sent["done"]:
            sent["done"] = True
            return {
                "type": "http.request",
                "body": b"".join(chunks),
                "more_body": keep_reading,
            }
        found: dict[str, Any] = await original()
        return found

    return receive
