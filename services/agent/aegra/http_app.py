"""Aegra custom FastAPI application (``http.app`` entry point)."""

from __future__ import annotations

import copy
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent.aegra.a2a_routes import router as a2a_router
from agent.aegra.admin_routes import router as admin_router
from agent.aegra.admission import AdmissionControlMiddleware
from agent.aegra.analytics_routes import router as analytics_router
from agent.aegra.answer_notes_routes import router as answer_notes_router
from agent.aegra.app_models import (
    AgentStructureOut,
    HealthProbeOut,
    VersionOut,
)
from agent.aegra.approval_audit import ApprovalAuditMiddleware
from agent.aegra.attachment_routes import router as attachment_router
from agent.aegra.auth_helpers import authenticated_user_id
from agent.aegra.channel_routes import router as channel_router
from agent.aegra.command_routes import router as command_router
from agent.aegra.config_editing_routes import register as register_config_editing
from agent.aegra.costs_routes import router as costs_router
from agent.aegra.document_routes import router as document_router
from agent.aegra.eval_routes import eval_mgmt_router
from agent.aegra.eval_routes import router as eval_router
from agent.aegra.extension_routes import router as extension_router
from agent.aegra.feature_routes import router as feature_router
from agent.aegra.feedback import feedback_router
from agent.aegra.fork_routes import router as fork_router
from agent.aegra.handoff_routes import router as handoff_router
from agent.aegra.health import health_response
from agent.aegra.inbound_limit_middleware import InboundLimitMiddleware
from agent.aegra.knowledge_routes import router as knowledge_router
from agent.aegra.limits_routes import router as limits_router
from agent.aegra.mcp_crypto import McpKeyMissingError
from agent.aegra.mcp_routes import router as mcp_router
from agent.aegra.mcp_server_routes import router as mcp_server_router
from agent.aegra.my_data_routes import router as my_data_router
from agent.aegra.personalization_routes import router as personalization_router
from agent.aegra.projects_routes import projects_router
from agent.aegra.rates_routes import router as rates_router
from agent.aegra.reasoning_routes import router as reasoning_router
from agent.aegra.search_routes import router as search_router
from agent.aegra.security_middleware import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    StreamingBodyLimitMiddleware,
)
from agent.aegra.share_routes import router as share_router
from agent.aegra.skill_routes import router as skill_router
from agent.aegra.space_routes import router as space_router
from agent.aegra.speech_routes import router as speech_router
from agent.aegra.tag_routes import router as tag_router
from agent.aegra.thread_cleanup import thread_cleanup_router
from agent.aegra.truncate_routes import router as truncate_router
from agent.aegra.upload_routes import upload_router
from agent.aegra.user_admin_routes import router as user_admin_router
from agent.aegra.workspace_routes import router as workspace_router
from agent.src.agent.config import agent_config
from agent.src.settings import settings
from agent.utils.pylogger import (
    bind_request_context,
    clear_request_context,
    get_python_logger,
)

logger = get_python_logger()


def _patch_aegra_persistence_if_inmemory() -> None:
    """Disable aegra_api database initialization when running in-memory mode."""
    import os

    disable_persistence = os.environ.get("AEGRA_DISABLE_PERSISTENCE", "").lower() in (
        "true",
        "1",
    )
    use_inmemory = os.environ.get("USE_INMEMORY_SAVER", "").lower() in ("true", "1")

    if not (disable_persistence or use_inmemory):
        return

    try:
        from aegra_api.core.database import db_manager

        async def _noop_initialize() -> None:
            logger.info("aegra_db_initialize_skipped_inmemory_mode")

        db_manager.initialize = _noop_initialize
        logger.info("aegra_persistence_patched_for_inmemory_mode")
    except ImportError:
        pass


_patch_aegra_persistence_if_inmemory()

from agent.aegra.shutdown import register_atexit  # noqa: E402

register_atexit()


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from agent.aegra.startup import run_startup
    from agent.src.observability.otel_setup import (
        setup_otel_metrics,
        setup_otel_traces,
    )

    await run_startup()
    setup_otel_metrics(settings, logger)
    setup_otel_traces(_app, settings, logger)
    _verify_custom_thread_delete(_app)
    yield


def _verify_custom_thread_delete(application: FastAPI) -> None:
    """Verify our custom DELETE /threads/{id} takes priority over Aegra's built-in."""
    from agent.aegra.thread_cleanup import delete_thread_with_cleanup

    for route in application.routes:
        if (
            hasattr(route, "path")
            and route.path == "/threads/{thread_id}"
            and hasattr(route, "methods")
            and "DELETE" in route.methods
        ):
            if getattr(route, "endpoint", None) is delete_thread_with_cleanup:
                logger.info("custom_thread_delete_route_verified")
                return
            raise RuntimeError(
                "custom_thread_delete_route_overridden: "
                "Aegra's built-in DELETE /threads/{thread_id} is taking "
                "priority over our custom cleanup handler. "
                "Check router registration order in http_app.py."
            )
    logger.warning("thread_delete_route_not_found")


app = FastAPI(title="template-agent-custom", lifespan=_lifespan)


@app.exception_handler(McpKeyMissingError)
async def mcp_key_missing_handler(
    request: Request, exc: McpKeyMissingError
) -> JSONResponse:
    """Answer a missing token-encryption key with what is missing."""
    logger.error("MCP token encryption key missing: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": str(exc),
            "error_type": "configuration_error",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with PII scrubbing for production."""
    from agent.src.pii_scrubber import scrub_error_response

    logger.error(
        "Unhandled exception: %s",
        exc,
        exc_info=True,
        extra={"path": request.url.path, "method": request.method},
    )

    error_response = scrub_error_response(
        detail="An unexpected error occurred. Please try again later.",
        exc=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _inbound_trace_id(request: Request) -> str | None:
    """The W3C trace id for this request, if there is one."""
    from agent.utils.pylogger import current_otel_ids

    otel_trace_id, _ = current_otel_ids()
    if otel_trace_id:
        return otel_trace_id

    match = _TRACEPARENT.match(request.headers.get("traceparent", "").strip().lower())
    if match and match.group(1) != "0" * 32:
        return match.group(1)
    return None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Extract correlation headers and bind them to the structured log context."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Extract correlation headers and bind to structured log context."""
        trace_id = (
            request.headers.get("x-trace-id")
            or _inbound_trace_id(request)
            or uuid4().hex
        )
        request_id = request.headers.get("x-request-id") or uuid4().hex
        org_id = request.headers.get("x-org-id")
        agent_id = request.headers.get("x-agent-id")
        user_id = request.headers.get("x-user-id")
        bind_request_context(
            trace_id=trace_id,
            request_id=request_id,
            org_id=org_id,
            agent_id=agent_id,
            user_id=user_id,
            thread_id=_thread_in(request.url.path),
        )
        try:
            from opentelemetry import trace as otel_trace

            span = otel_trace.get_current_span()
            if span is not None and span.is_recording():
                span.set_attribute("app.trace_id", trace_id)
        except ImportError:
            pass
        try:
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_request_context()


_THREAD_IN_PATH = re.compile(r"/threads/([^/]+)")


def _thread_in(path: str) -> str | None:
    """The conversation this request is about, from its path."""
    found = _THREAD_IN_PATH.search(path)
    return found.group(1) if found else None


app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
_MULTIPART_OVERHEAD_ALLOWANCE = 64 * 1024

_UPLOAD_BODY_LIMIT = settings.UPLOAD_MAX_ARCHIVE_BYTES + _MULTIPART_OVERHEAD_ALLOWANCE
_BODY_LIMITS = {"/upload": _UPLOAD_BODY_LIMIT}

app.add_middleware(
    StreamingBodyLimitMiddleware,
    max_size_bytes=settings.REQUEST_BODY_MAX_SIZE,
    path_limits=_BODY_LIMITS,
)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size_bytes=settings.REQUEST_BODY_MAX_SIZE,
    path_limits=_BODY_LIMITS,
)
app.add_middleware(
    AdmissionControlMiddleware, max_concurrent=settings.MAX_CONCURRENT_RUNS
)
app.add_middleware(InboundLimitMiddleware)
app.add_middleware(ApprovalAuditMiddleware)
app.include_router(mcp_server_router)
app.include_router(a2a_router)
app.include_router(knowledge_router)
app.include_router(limits_router)
app.include_router(costs_router)
app.include_router(my_data_router)
app.include_router(handoff_router)
app.include_router(thread_cleanup_router)
app.include_router(skill_router)
app.include_router(document_router)
app.include_router(personalization_router)
app.include_router(extension_router)
app.include_router(rates_router)
app.include_router(speech_router)
register_config_editing(app)
app.include_router(user_admin_router)
app.include_router(space_router)
app.include_router(truncate_router)
app.include_router(workspace_router)
app.include_router(projects_router)
app.include_router(mcp_router)
app.include_router(feedback_router)
app.include_router(admin_router)
app.include_router(eval_router)
app.include_router(eval_mgmt_router)
app.include_router(channel_router)
app.include_router(search_router)
app.include_router(answer_notes_router)
app.include_router(feature_router)
app.include_router(command_router)
app.include_router(reasoning_router)
app.include_router(fork_router)
app.include_router(attachment_router)
app.include_router(analytics_router)
app.include_router(tag_router)
app.include_router(share_router)
app.include_router(upload_router)


@app.get("/livez", responses={200: {"model": HealthProbeOut}})
@app.get("/healthz", responses={200: {"model": HealthProbeOut}})
@app.get("/readyz", responses={200: {"model": HealthProbeOut}})
async def health_probes(request: Request) -> JSONResponse:
    """Kubernetes probe endpoints, served from agent.aegra.health."""
    code, body = await health_response(request.url.path)
    return JSONResponse(status_code=code, content=body)


@app.get("/version", responses={200: {"model": VersionOut}})
def version() -> dict[str, str]:
    """Return service name and version."""
    from agent.aegra import __version__

    return {"service": "template-agent", "version": __version__}


@app.get("/config/agent-structure", responses={200: {"model": AgentStructureOut}})
async def agent_structure(request: Request) -> dict:
    """Return the agent structure in a dict from config."""
    await authenticated_user_id(request)
    name: str = agent_config.get_name()

    orchestrator: dict[str, Any] = copy.deepcopy(agent_config.get_orchestrator_config())
    orchestrator.pop("body", None)
    orchestrator.pop("skill_paths", None)

    subagents: dict[str, dict[str, Any]] = copy.deepcopy(
        agent_config.get_all_subagent_configs()
    )
    for key in subagents:
        subagents[key].pop("body", None)
        subagents[key].pop("skill_paths", None)

    mcp_servers: dict[str, Any] = copy.deepcopy(agent_config.get_mcp_servers())
    for key in mcp_servers:
        mcp_servers[key].pop("ssl_verify", None)
        mcp_servers[key].pop("oauth", None)
        mcp_servers[key].pop("auth_env_var", None)

    available_skills: list[str] = list(agent_config.get_available_skills())

    return {
        "name": name,
        "orchestrator": orchestrator,
        "subagents": subagents,
        "mcp_servers": mcp_servers,
        "available_skills": available_skills,
    }
