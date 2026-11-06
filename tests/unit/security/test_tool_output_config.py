"""Which servers a deployment vouches for, as configuration."""

from __future__ import annotations

from agent.src.agent.config.middleware import (
    MiddlewareDefaults,
    MiddlewareFileConfig,
    ToolOutputConfig,
    resolve_middleware,
)


def test_nothing_is_trusted_by_default():
    assert ToolOutputConfig().trusted_servers == []


def test_servers_can_be_vouched_for():
    assert ToolOutputConfig(trusted_servers=["docs"]).trusted_servers == ["docs"]


def test_defaults_carry_a_tool_output_section():
    assert MiddlewareDefaults().tool_output.trusted_servers == []


def test_the_section_is_read_from_the_config_file():
    parsed = MiddlewareFileConfig.model_validate(
        {"defaults": {"tool_output": {"trusted_servers": ["docs", "wiki"]}}}
    )
    assert parsed.defaults.tool_output.trusted_servers == ["docs", "wiki"]


def test_the_resolved_config_exposes_it():
    file_config = MiddlewareFileConfig(
        defaults=MiddlewareDefaults(
            tool_output=ToolOutputConfig(trusted_servers=["docs"])
        )
    )
    resolved = resolve_middleware(file_config, "any-model")
    assert resolved.tool_output.trusted_servers == ["docs"]


def test_an_agent_can_override_the_trusted_list():
    file_config = MiddlewareFileConfig(
        defaults=MiddlewareDefaults(
            tool_output=ToolOutputConfig(trusted_servers=["docs"])
        )
    )
    resolved = resolve_middleware(
        file_config, "any-model", {"tool_output": {"trusted_servers": ["tracker"]}}
    )
    assert resolved.tool_output.trusted_servers == ["tracker"]


def test_an_existing_config_without_the_section_still_resolves():
    resolved = resolve_middleware(MiddlewareFileConfig(), "any-model")
    assert resolved.tool_output.trusted_servers == []
