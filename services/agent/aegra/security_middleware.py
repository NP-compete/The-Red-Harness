"""Production security middleware for HTTP security headers and request validation."""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Add security headers to response."""
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        response.headers["Content-Security-Policy"] = "default-src 'self'"

        if request.url.scheme == "https" or settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


UPLOAD_PATHS = ("/knowledge/documents", "/knowledge/sources")
UPLOAD_SUFFIXES = ("/attachments", "/state")

UPLOAD_HEADROOM = 6


def body_limit_for(
    path: str, *, overrides: dict[str, int], normal: int, upload: int
) -> int:
    """How many bytes this path may carry."""
    if path in overrides:
        return overrides[path]
    if path.endswith(UPLOAD_SUFFIXES) or path.startswith(UPLOAD_PATHS):
        return upload
    return normal


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce request body size limits to prevent DoS attacks."""

    def __init__(
        self,
        app: Any,
        max_size_bytes: int = 10 * 1024 * 1024,
        upload_max_bytes: int | None = None,
        path_limits: dict[str, int] | None = None,
    ):
        """Initialize with configurable max request body size."""
        super().__init__(app)
        self.max_size_bytes = max_size_bytes
        self.upload_max_bytes = upload_max_bytes or (max_size_bytes * UPLOAD_HEADROOM)
        self.path_limits = path_limits or {}
        logger.info(
            "Request body size limit: %d bytes (uploads: %d, overrides: %s)",
            max_size_bytes,
            self.upload_max_bytes,
            self.path_limits or "none",
        )

    def limit_for(self, path: str) -> int:
        """Return the body size limit that applies to a path."""
        return body_limit_for(
            path,
            overrides=self.path_limits,
            normal=self.max_size_bytes,
            upload=self.upload_max_bytes,
        )

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Check declared request body size before processing."""
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        limit = self.limit_for(request.url.path)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > limit:
            logger.warning(
                "Request body too large: %s bytes (max %d) on %s",
                content_length,
                limit,
                request.url.path,
            )
            return _too_large(limit)

        return await call_next(request)


def _too_large(limit: int) -> JSONResponse:
    """Build the 413 returned when a body exceeds its limit."""
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={
            "detail": f"Request body exceeds maximum size of {limit} bytes",
            "error_type": "request_too_large",
        },
    )


class StreamingBodyLimitMiddleware:
    """Cap request body bytes as they arrive, before anything parses them."""

    def __init__(
        self,
        app: Any,
        max_size_bytes: int,
        path_limits: dict[str, int] | None = None,
        upload_max_bytes: int | None = None,
    ):
        """Initialize with a default limit and optional per-path overrides."""
        self.app = app
        self.max_size_bytes = max_size_bytes
        self.path_limits = path_limits or {}
        self.upload_max_bytes = upload_max_bytes or (max_size_bytes * UPLOAD_HEADROOM)

    def limit_for(self, path: str) -> int:
        """Return the body size limit that applies to a path."""
        return body_limit_for(
            path,
            overrides=self.path_limits,
            normal=self.max_size_bytes,
            upload=self.upload_max_bytes,
        )

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Count streamed body bytes and abort the request past the limit."""
        if scope["type"] != "http" or scope.get("method") in (
            "GET",
            "HEAD",
            "OPTIONS",
        ):
            await self.app(scope, receive, send)
            return

        limit = self.limit_for(scope.get("path", ""))
        state = {"received": 0, "exceeded": False, "sent": False}

        async def limited_receive() -> Any:
            message = await receive()
            if message["type"] == "http.request":
                state["received"] += len(message.get("body", b""))
                if state["received"] > limit:
                    state["exceeded"] = True
                    logger.warning(
                        "Streamed body exceeded limit on %s: %d bytes (max %d)",
                        scope.get("path", ""),
                        state["received"],
                        limit,
                    )
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Any) -> None:
            if state["exceeded"]:
                return
            state["sent"] = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not state["exceeded"]:
                raise

        if state["exceeded"] and not state["sent"]:
            await _too_large(limit)(scope, receive, send)
