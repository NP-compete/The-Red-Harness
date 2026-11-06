"""The decision path, against the configuration this repository ships."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agent.src.agent.config.middleware import (
    MiddlewareFileConfig,
    resolve_middleware,
)
from agent.src.security.guard import build_guard
from agent.src.security.resolver import (
    Allowed,
    Identity,
    NeedsApproval,
    RefusalCode,
    Refused,
    ToolCall,
)

CONFIG = (
    Path(__file__).resolve().parents[3] / "config" / "agent" / "runtime" / "agent.yaml"
)
SOMEONE = Identity(subject="someone@example.com")


class Connected:
    async def has_valid_token(self, user_id, mcp_name, server_cfg, *, verify=False):
        return True


@pytest.fixture()
def shipped():
    raw = yaml.safe_load(CONFIG.read_text())
    file_config = MiddlewareFileConfig.model_validate(
        {
            "defaults": raw.get("middleware", {}),
            "profiles": raw.get("harness_profiles", {}),
        }
    )
    return resolve_middleware(file_config, "any-model")


def guard_for(shipped, **kwargs):
    return build_guard(
        config=shipped,
        credentials=Connected(),
        servers={"tracker": {"url": "https://tracker"}},
        identity=SOMEONE,
        **kwargs,
    )


def test_the_shipped_configuration_loads(shipped):
    assert shipped.human_approval.enabled is True


def test_reading_a_file_is_allowed_without_asking(shipped):
    assert isinstance(guard_for(shipped).authorise(ToolCall(name="read_file")), Allowed)


def test_an_internal_bookkeeping_tool_does_not_prompt(shipped):
    assert isinstance(
        guard_for(shipped).authorise(ToolCall(name="write_todos")), Allowed
    )


def test_an_unrecognised_tool_asks_rather_than_running_silently(shipped):
    decision = guard_for(shipped).authorise(ToolCall(name="unheard_of_tool"))
    assert isinstance(decision, NeedsApproval)


def test_an_unconnected_system_is_refused_before_policy_matters(shipped):
    guard = build_guard(
        config=shipped,
        credentials=Connected(),
        servers={},
        identity=SOMEONE,
    )
    decision = guard.authorise(ToolCall(name="tracker.search", server="tracker"))
    assert isinstance(decision, Refused)
    assert decision.code is RefusalCode.NO_AUTHORITY


def test_a_dry_run_refuses_what_would_have_asked(shipped):
    decision = guard_for(shipped, effects="dry_run").authorise(
        ToolCall(name="unheard_of_tool")
    )
    assert isinstance(decision, Refused)
    assert "dry run" in decision.message


def test_nothing_is_vouched_for_by_default(shipped):
    assert shipped.tool_output.trusted_servers == []


def test_every_decision_against_the_shipped_config_is_recorded(shipped):
    guard = guard_for(shipped)
    guard.authorise(ToolCall(name="read_file"))
    guard.authorise(ToolCall(name="unheard_of_tool"))
    assert len(guard.journal.entries) == 2
