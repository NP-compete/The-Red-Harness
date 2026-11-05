"""What this agent publishes to a system calling it."""

from __future__ import annotations

import pytest

from agent.src.agent.config.inbound import PublishedTool
from agent.src.agent.config.tool_projection import (
    SCHEMA_FOR,
    project_tools,
)

ASK = PublishedTool(name="ask", description="Ask this agent a question", scope="read")
ACT = PublishedTool(name="do", description="Ask, and let it act", scope="act")


class TestWhatIsPublished:
    def test_a_declared_tool_appears(self):
        assert [t["name"] for t in project_tools((ASK,))] == ["ask"]

    def test_its_description_travels(self):
        assert project_tools((ASK,))[0]["description"].startswith("Ask")

    def test_a_tool_with_no_description_still_publishes(self):
        bare = PublishedTool(name="ask", description="", scope="read")
        assert project_tools((bare,))[0]["name"] == "ask"

    def test_several_keep_their_order(self):
        assert [t["name"] for t in project_tools((ACT, ASK))] == ["do", "ask"]

    def test_nothing_declared_publishes_nothing(self):
        assert project_tools(()) == []


class TestWhatIsNotPublished:
    def test_a_skill_does_not_become_a_tool(self):
        from unittest.mock import patch

        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_available_skills",
            return_value={"invent_a_skill": "/tmp/x"},
        ):
            assert [t["name"] for t in project_tools((ASK,))] == ["ask"]

    def test_an_mcp_server_the_agent_uses_does_not_become_a_tool(self):
        from unittest.mock import patch

        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_mcp_servers",
            return_value={"somebody_elses_server": {"enabled": True}},
        ):
            assert [t["name"] for t in project_tools((ASK,))] == ["ask"]


class TestTheInputSchema:
    def test_every_tool_has_one(self):
        assert project_tools((ASK,))[0]["inputSchema"]["type"] == "object"

    def test_a_question_is_required(self):
        found = project_tools((ASK,))[0]["inputSchema"]
        assert found["required"] == ["question"]

    def test_a_conversation_may_be_continued(self):
        found = project_tools((ASK,))[0]["inputSchema"]
        assert "thread_id" in found["properties"]

    def test_the_conversation_is_optional(self):
        found = project_tools((ASK,))[0]["inputSchema"]
        assert "thread_id" not in found["required"]

    def test_no_extra_arguments_are_accepted(self):
        found = project_tools((ASK,))[0]["inputSchema"]
        assert found["additionalProperties"] is False

    def test_the_schema_is_the_same_for_both_scopes(self):
        assert (
            project_tools((ASK,))[0]["inputSchema"]
            == project_tools((ACT,))[0]["inputSchema"]
        )


class TestScope:
    def test_it_is_not_sent_to_the_caller_as_a_field(self):
        assert "scope" not in project_tools((ACT,))[0]["inputSchema"]["properties"]

    def test_it_is_still_reachable_for_the_run_to_enforce(self):
        from agent.src.agent.config.tool_projection import scope_of

        assert scope_of("do", (ACT, ASK)) == "act"

    def test_an_undeclared_tool_has_no_scope(self):
        from agent.src.agent.config.tool_projection import scope_of

        assert scope_of("something_else", (ACT, ASK)) is None


class TestTheSchemaIsOneThing:
    def test_both_scopes_share_the_declaration(self):
        assert SCHEMA_FOR["read"] is SCHEMA_FOR["act"]

    @pytest.mark.parametrize("scope", ["read", "act"])
    def test_a_known_scope_has_a_schema(self, scope):
        assert SCHEMA_FOR[scope]["type"] == "object"
