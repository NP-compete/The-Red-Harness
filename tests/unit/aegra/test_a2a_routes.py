"""Being discovered and delegated to by another agent."""

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


def _card(client, *, door=OPEN, caller="svc-a"):
    with (
        patch(
            "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
            return_value=door,
        ),
        patch("agent.aegra.a2a_routes._caller", return_value=caller),
    ):
        return client.get("/.well-known/agent-card.json")


def _send(client, text="hello", *, door=OPEN, caller="svc-a", answer=None):
    patches = [
        patch(
            "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
            return_value=door,
        ),
        patch("agent.aegra.a2a_routes._caller", return_value=caller),
    ]
    if answer is not None:
        patches.append(patch("agent.aegra.a2a_routes._run", return_value=answer))
    for p in patches:
        p.start()
    try:
        return client.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": text}],
                        "messageId": "m1",
                    }
                },
            },
        )
    finally:
        for p in reversed(patches):
            p.stop()


class TestADoorThatIsShut:
    def test_there_is_no_card(self, client):
        assert _card(client, door=SHUT).status_code == 404

    def test_nothing_can_be_delegated(self, client):
        assert _send(client, door=SHUT).status_code == 404


class TestTheCardAnybodyCanRead:
    """A peer has to read how to authenticate before it can."""

    def test_it_is_served_without_an_identity(self, client):
        assert _card(client, caller="").status_code == 200

    def test_it_names_the_agent(self, client):
        assert _card(client, caller="").json()["name"]

    def test_it_says_where_to_send_work(self, client):
        assert _card(client, caller="").json()["url"].endswith("/a2a")

    def test_it_says_how_to_authenticate(self, client):
        assert _card(client, caller="").json()["securitySchemes"]

    def test_it_lists_no_capabilities(self, client):
        assert _card(client, caller="").json()["skills"] == []

    def test_it_says_there_is_more_behind_authentication(self, client):
        assert (
            _card(client, caller="").json()["supportsAuthenticatedExtendedCard"] is True
        )


class TestTheCardAnIdentifiedPeerReads:
    def test_it_lists_the_declared_capability(self, client):
        found = _card(client).json()
        assert [s["id"] for s in found["skills"]] == ["ask"]

    def test_the_capability_carries_its_description(self, client):
        assert _card(client).json()["skills"][0]["description"]

    def test_a_skill_of_the_agent_is_not_a_capability_on_the_card(self, client):
        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_available_skills",
            return_value={"invented": "/tmp/x"},
        ):
            assert [s["id"] for s in _card(client).json()["skills"]] == ["ask"]


class TestDelegatingATask:
    ANSWERED = {"text": "It is 750.", "thread_id": "t1", "paused": None}

    def test_an_unidentified_peer_is_refused(self, client):
        assert _send(client, caller="", answer=self.ANSWERED).status_code == 401

    def test_the_answer_comes_back(self, client):
        found = _send(client, answer=self.ANSWERED).json()
        assert found["result"]["parts"][0]["text"] == "It is 750."

    def test_it_comes_back_as_something_the_peer_said_to(self, client):
        found = _send(client, answer=self.ANSWERED).json()
        assert found["result"]["role"] == "agent"

    def test_the_task_can_be_continued(self, client):
        found = _send(client, answer=self.ANSWERED).json()
        assert found["result"]["contextId"] == "t1"

    def test_a_message_with_no_text_is_refused(self, client):
        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=OPEN,
            ),
            patch("agent.aegra.a2a_routes._caller", return_value="svc-a"),
        ):
            found = client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "message/send",
                    "params": {
                        "message": {"role": "user", "parts": [], "messageId": "m1"}
                    },
                },
            )
        assert "error" in found.json()


class TestATaskThatNeedsADecision:
    PAUSED = {
        "text": "",
        "thread_id": "t1",
        "paused": {"awaiting": [{"action": "write_file"}], "thread_id": "t1"},
    }

    def test_it_comes_back_as_a_task_rather_than_a_hang(self, client):
        found = _send(client, answer=self.PAUSED)
        assert found.status_code == 200

    def test_the_task_says_it_is_waiting_on_somebody(self, client):
        found = _send(client, answer=self.PAUSED).json()
        assert found["result"]["status"]["state"] == "input-required"

    def test_it_says_what_is_waiting(self, client):
        found = _send(client, answer=self.PAUSED).json()
        said = found["result"]["status"]["message"]["parts"][0]["text"]
        assert "write_file" in said

    def test_it_carries_the_task_to_resume(self, client):
        found = _send(client, answer=self.PAUSED).json()
        assert found["result"]["contextId"] == "t1"


class TestItReusesTheOneAuthorityDecision:
    """A second place answering "whose run is this" is how the two"""

    @staticmethod
    def _metadata(client, door):
        seen = {}

        async def _spy(**kwargs):
            seen.update(kwargs.get("metadata") or {})
            return {"text": "ok", "thread_id": "t1", "paused": None}

        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=door,
            ),
            patch("agent.aegra.a2a_routes._caller", return_value="alice"),
            patch("agent.aegra.a2a_routes._run", new=_spy),
        ):
            client.post(
                "/a2a",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": "hi"}],
                            "messageId": "m1",
                        }
                    },
                },
            )
        return seen

    def test_a_service_peer_does_not_become_a_person(self, client):
        assert self._metadata(client, OPEN)["user_id"] != "alice"

    def test_a_service_peer_cannot_use_connections(self, client):
        assert self._metadata(client, OPEN)["may_use_connections"] is False

    def test_a_person_delegating_keeps_their_own_identity(self, client):
        door = Inbound(enabled=True, auth_mode="oauth", tools=(ASK,))
        assert self._metadata(client, door)["user_id"] == "alice"

    def test_it_is_the_same_function_both_dialects_use(self, client):
        import inspect

        from agent.aegra import a2a_routes, mcp_server_routes

        assert "authority_for" in inspect.getsource(a2a_routes)
        assert "authority_for" in inspect.getsource(mcp_server_routes)


class TestTheProtocolItself:
    def test_an_unknown_method_is_a_protocol_error(self, client):
        with (
            patch(
                "agent.src.agent.config.loader.AgentConfig.get_inbound_config",
                return_value=OPEN,
            ),
            patch("agent.aegra.a2a_routes._caller", return_value="svc-a"),
        ):
            found = client.post(
                "/a2a", json={"jsonrpc": "2.0", "id": 1, "method": "nonsense"}
            )
        assert found.json()["error"]["code"] == -32601

    def test_the_request_id_comes_back(self, client):
        assert _send(client, answer=TestDelegatingATask.ANSWERED).json()["id"] == 1
