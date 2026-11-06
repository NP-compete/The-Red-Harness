"""The door another system calls this agent through."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from agent.src.agent.config.inbound import Inbound, PublishedTool

ASK = PublishedTool(name="ask", description="Ask this agent", scope="read")
OPEN = Inbound(enabled=True, auth_mode="service_token", tools=(ASK,))
SHUT = Inbound()


@pytest.fixture
def client() -> TestClient:
    from agent.aegra.http_app import app

    return TestClient(app)


def _rpc(client, method, params=None, *, door=OPEN, answer=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params

    patches = [
        patch(
            "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
            return_value=door,
        ),
        patch(
            "agent.aegra.mcp_server_routes._caller",
            return_value="svc-a",
        ),
    ]
    if answer is not None:
        patches.append(patch("agent.aegra.mcp_server_routes._run", return_value=answer))

    for p in patches:
        p.start()
    try:
        return client.post("/mcp/server", json=body)
    finally:
        for p in reversed(patches):
            p.stop()


class TestADoorThatIsShut:
    def test_it_is_not_there_at_all(self, client):
        assert _rpc(client, "tools/list", door=SHUT).status_code == 404

    def test_nothing_can_be_called_through_it(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "hi"}},
            door=SHUT,
        )
        assert found.status_code == 404


class TestSayingWhatItIs:
    def test_it_answers_initialize(self, client):
        found = _rpc(client, "initialize", {})
        assert found.status_code == 200

    def test_it_names_a_protocol_version(self, client):
        found = _rpc(client, "initialize", {}).json()
        assert found["result"]["protocolVersion"]

    def test_it_says_it_has_tools(self, client):
        found = _rpc(client, "initialize", {}).json()
        assert "tools" in found["result"]["capabilities"]

    def test_it_gives_itself_a_name(self, client):
        found = _rpc(client, "initialize", {}).json()
        assert found["result"]["serverInfo"]["name"]


class TestListingTools:
    def test_the_declared_tool_is_listed(self, client):
        found = _rpc(client, "tools/list").json()
        assert [t["name"] for t in found["result"]["tools"]] == ["ask"]

    def test_each_carries_its_input_schema(self, client):
        found = _rpc(client, "tools/list").json()
        assert found["result"]["tools"][0]["inputSchema"]["type"] == "object"

    def test_a_door_with_no_tools_lists_none(self, client):
        bare = Inbound(enabled=True, auth_mode="service_token", tools=())
        found = _rpc(client, "tools/list", door=bare).json()
        assert found["result"]["tools"] == []


class TestCallingATool:
    ANSWERED = {"text": "It is 750.", "thread_id": "t1", "paused": None}

    def test_the_answer_comes_back(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "what is the limit?"}},
            answer=self.ANSWERED,
        ).json()
        assert found["result"]["content"][0]["text"] == "It is 750."

    def test_it_is_not_flagged_as_an_error(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "hi"}},
            answer=self.ANSWERED,
        ).json()
        assert found["result"]["isError"] is False

    def test_the_conversation_comes_back_so_it_can_be_continued(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "hi"}},
            answer=self.ANSWERED,
        ).json()
        assert found["result"]["structuredContent"]["thread_id"] == "t1"

    def test_a_tool_nobody_declared_is_refused(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "drop_everything", "arguments": {"question": "hi"}},
            answer=self.ANSWERED,
        ).json()
        assert found["result"]["isError"] is True

    def test_a_call_with_no_question_is_refused(self, client):
        found = _rpc(
            client, "tools/call", {"name": "ask", "arguments": {}}, answer=self.ANSWERED
        ).json()
        assert found["result"]["isError"] is True

    def test_the_refusal_says_what_was_missing(self, client):
        found = _rpc(
            client, "tools/call", {"name": "ask", "arguments": {}}, answer=self.ANSWERED
        ).json()
        assert "question" in found["result"]["content"][0]["text"]


class TestARunThatStopsForADecision:
    """A caller with nobody behind it cannot be left hanging."""

    PAUSED = {
        "text": "",
        "thread_id": "t1",
        "paused": {"awaiting": [{"action": "write_file"}], "thread_id": "t1"},
    }

    def test_it_comes_back_as_a_result_not_a_hang(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "write a file"}},
            answer=self.PAUSED,
        )
        assert found.status_code == 200

    def test_it_says_what_is_waiting(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "write a file"}},
            answer=self.PAUSED,
        ).json()
        assert "write_file" in found["result"]["content"][0]["text"]

    def test_it_is_not_an_error(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "write a file"}},
            answer=self.PAUSED,
        ).json()
        assert found["result"]["isError"] is False

    def test_it_carries_the_conversation_to_resume(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "write a file"}},
            answer=self.PAUSED,
        ).json()
        assert found["result"]["structuredContent"]["thread_id"] == "t1"

    def test_it_is_marked_as_waiting_in_a_way_a_program_can_read(self, client):
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "write a file"}},
            answer=self.PAUSED,
        ).json()
        assert found["result"]["structuredContent"]["status"] == "awaiting_decision"


class TestWhoseAuthorityTheRunCarries:
    def test_a_caller_it_cannot_identify_is_refused(self, client):
        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=OPEN,
            ),
            patch("agent.aegra.mcp_server_routes._caller", return_value=""),
        ):
            found = client.post(
                "/mcp/server",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "ask", "arguments": {"question": "hi"}},
                },
            )
        assert found.status_code == 401

    def test_listing_tools_also_needs_an_identity(self, client):
        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=OPEN,
            ),
            patch("agent.aegra.mcp_server_routes._caller", return_value=""),
        ):
            found = client.post(
                "/mcp/server",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
        assert found.status_code == 401

    def test_the_run_is_started_as_the_caller(self, client):
        seen = {}

        async def _spy(
            *, caller, question, thread_id, scope, authorization="", metadata=None
        ):
            seen["caller"] = caller
            seen["authorization"] = authorization
            return {"text": "ok", "thread_id": "t1", "paused": None}

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=OPEN,
            ),
            patch("agent.aegra.mcp_server_routes._caller", return_value="svc-a"),
            patch("agent.aegra.mcp_server_routes._run", new=_spy),
        ):
            client.post(
                "/mcp/server",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "ask", "arguments": {"question": "hi"}},
                },
            )
        assert seen["caller"] == "svc-a"


class TestTheProtocolItself:
    def test_an_unknown_method_is_a_protocol_error(self, client):
        found = _rpc(client, "nonsense/method").json()
        assert found["error"]["code"] == -32601

    def test_the_request_id_comes_back(self, client):
        found = _rpc(client, "tools/list").json()
        assert found["id"] == 1

    def test_a_protocol_error_is_not_a_tool_error(self, client):
        found = _rpc(client, "nonsense/method").json()
        assert "result" not in found

    def test_the_callers_credential_travels_to_the_run(self, client):
        seen = {}

        async def _spy(
            *, caller, question, thread_id, scope, authorization="", metadata=None
        ):
            seen["authorization"] = authorization
            return {"text": "ok", "thread_id": "t1", "paused": None}

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=OPEN,
            ),
            patch("agent.aegra.mcp_server_routes._caller", return_value="svc-a"),
            patch("agent.aegra.mcp_server_routes._run", new=_spy),
        ):
            client.post(
                "/mcp/server",
                headers={"Authorization": "Bearer abc"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "ask", "arguments": {"question": "hi"}},
                },
            )
        assert seen["authorization"] == "Bearer abc"


class TestTheRunIsGivenAnAuthority:
    """The door must make the decision, not merely have it available."""

    @staticmethod
    def _metadata_for(client, door, caller="alice"):
        seen = {}

        async def _spy(
            *, caller, question, thread_id, scope, authorization="", metadata=None
        ):
            seen.update(metadata or {})
            return {"text": "ok", "thread_id": "t1", "paused": None}

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=door,
            ),
            patch("agent.aegra.mcp_server_routes._caller", return_value=caller),
            patch("agent.aegra.mcp_server_routes._run", new=_spy),
        ):
            client.post(
                "/mcp/server",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "ask", "arguments": {"question": "hi"}},
                },
            )
        return seen

    def test_a_service_token_run_is_not_a_persons(self, client):
        door = Inbound(enabled=True, auth_mode="service_token", tools=(ASK,))
        assert self._metadata_for(client, door)["user_id"] != "alice"

    def test_a_service_token_run_cannot_use_connections(self, client):
        door = Inbound(enabled=True, auth_mode="service_token", tools=(ASK,))
        assert self._metadata_for(client, door)["may_use_connections"] is False

    def test_an_oauth_run_belongs_to_the_caller(self, client):
        door = Inbound(enabled=True, auth_mode="oauth", tools=(ASK,))
        assert self._metadata_for(client, door)["user_id"] == "alice"

    def test_a_read_tool_uses_no_connections_even_for_a_person(self, client):
        door = Inbound(enabled=True, auth_mode="oauth", tools=(ASK,))
        assert self._metadata_for(client, door)["may_use_connections"] is False

    def test_an_act_tool_may_for_a_person(self, client):
        acting = PublishedTool(name="ask", description="", scope="act")
        door = Inbound(enabled=True, auth_mode="oauth", tools=(acting,))
        assert self._metadata_for(client, door)["may_use_connections"] is True

    def test_the_run_is_marked_as_having_come_from_outside(self, client):
        door = Inbound(enabled=True, auth_mode="oauth", tools=(ASK,))
        assert self._metadata_for(client, door)["inbound"] is True

    def test_a_door_with_an_impossible_mode_refuses_the_call(self, client):
        door = Inbound(enabled=True, auth_mode="agent", tools=(ASK,))
        found = _rpc(
            client,
            "tools/call",
            {"name": "ask", "arguments": {"question": "hi"}},
            door=door,
            answer={"text": "ok", "thread_id": "t1", "paused": None},
        ).json()
        assert found["result"]["isError"] is True
