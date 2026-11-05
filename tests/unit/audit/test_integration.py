"""Unit tests for platform audit middleware builder integration."""

from unittest.mock import MagicMock, patch

from agent.src.agent.config.middleware import ResolvedMiddlewareConfig
from agent.src.audit.middleware import AuditMiddleware
from agent.src.infrastructure.middleware import build_middleware_list


class TestBuildMiddlewareListAudit:
    def test_includes_audit_middleware_when_enabled(self):
        resolved = ResolvedMiddlewareConfig(summarization_tool_enabled=False)
        with (
            patch("agent.src.infrastructure.middleware.settings") as mock_settings,
            patch(
                "agent.src.audit.config.is_audit_enabled",
                return_value=True,
            ),
        ):
            mock_settings.MIDDLEWARE_ENABLED = True
            result = build_middleware_list(
                resolved, mcp_tool_names=frozenset({"tool_a"})
            )
        assert isinstance(result[0], AuditMiddleware)
        assert result[0]._mcp_tool_names == frozenset({"tool_a"})

    def test_no_audit_middleware_when_disabled(self):
        resolved = ResolvedMiddlewareConfig(summarization_tool_enabled=False)
        with (
            patch("agent.src.infrastructure.middleware.settings") as mock_settings,
            patch(
                "agent.src.audit.config.is_audit_enabled",
                return_value=False,
            ),
        ):
            mock_settings.MIDDLEWARE_ENABLED = True
            result = build_middleware_list(resolved)
        assert not any(isinstance(m, AuditMiddleware) for m in result)

    def test_audit_middleware_when_master_middleware_disabled(self):
        resolved = ResolvedMiddlewareConfig(summarization_tool_enabled=True)
        mock_mw = MagicMock()
        with (
            patch("agent.src.infrastructure.middleware.settings") as mock_settings,
            patch(
                "agent.src.audit.config.is_audit_enabled",
                return_value=True,
            ),
            patch(
                "agent.src.opa.config.is_opa_enabled",
                return_value=False,
            ),
            patch(
                "agent.src.infrastructure.middleware._build_summarization_tool_middleware",
                return_value=mock_mw,
            ),
        ):
            mock_settings.MIDDLEWARE_ENABLED = False
            result = build_middleware_list(resolved)
        assert isinstance(result[0], AuditMiddleware)
        assert len(result) == 10
        assert type(result[1]).__name__ == "GeminiSafetyLogMiddleware"
        assert type(result[2]).__name__ == "UserIdentityMiddleware"
        assert type(result[3]).__name__ == "AgentConfigMiddleware"
        assert type(result[4]).__name__ == "CurrentDatetimeMiddleware"
        assert type(result[5]).__name__ == "PromptSizeMiddleware"
        assert type(result[6]).__name__ == "McpAuthNoticeMiddleware"
        assert type(result[7]).__name__ == "ImageSanitizeMiddleware"


class TestInterruptIsNotAnError:
    """A human-approval pause is control flow, not a failure."""

    def test_graph_interrupt_is_classified_as_interrupted(self):
        from langgraph.errors import GraphInterrupt

        from agent.src.audit.middleware import _audit_status_for

        assert _audit_status_for(GraphInterrupt(())) == "interrupted"

    def test_a_real_failure_is_still_an_error(self):
        from agent.src.audit.middleware import _audit_status_for

        assert _audit_status_for(RuntimeError("boom")) == "error"
