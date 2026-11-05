"""What the agent is connected to, and what it knows how to do."""

from __future__ import annotations

import pytest

from agent.cli.inventory import InventoryFailed, list_servers, list_skills

SERVERS = {
    "servers": [
        {"name": "atlan", "display_name": "Atlan", "enabled": True, "auth_mode": "dcr"},
        {
            "name": "gitlab",
            "display_name": "GitLab",
            "enabled": False,
            "auth_mode": "none",
        },
    ]
}

CONNECTIONS = {
    "connections": [
        {"mcp_name": "atlan", "connected": True, "account": "someone@example.com"},
        {"mcp_name": "gitlab", "connected": False},
    ]
}

SKILLS = {
    "skills": [
        {"name": "data-discovery", "description": "Find a dataset."},
        {"name": "incident-triage", "description": "Work out what broke."},
    ]
}


class _Transport:
    def __init__(self, replies):
        self._replies = replies

    def get(self, path):
        return self._replies.get(path, (404, {"detail": "not found"}))

    def post(self, path, body=None):
        return self.get(path)


def _servers(servers=SERVERS, connections=CONNECTIONS, status=200):
    transport = _Transport(
        {
            "/mcp/servers": (status, servers),
            "/mcp/oauth/connections": (200, connections),
        }
    )
    return list_servers(transport=transport)


class TestServers:
    def test_it_reports_each_configured_server(self):
        assert len(_servers()) == 2

    def test_it_says_which_are_usable_now(self):
        found = {s.name: s for s in _servers()}
        assert found["atlan"].connected is True

    def test_it_says_which_are_not(self):
        found = {s.name: s for s in _servers()}
        assert found["gitlab"].connected is False

    def test_it_reports_who_the_connection_belongs_to(self):
        found = {s.name: s for s in _servers()}
        assert found["atlan"].account == "someone@example.com"

    def test_a_server_the_deployment_turned_off_says_so(self):
        found = {s.name: s for s in _servers()}
        assert found["gitlab"].enabled is False

    def test_a_refusal_is_not_an_empty_list(self):
        with pytest.raises(InventoryFailed):
            _servers(status=403)

    def test_connections_it_cannot_read_do_not_lose_the_servers(self):
        transport = _Transport(
            {
                "/mcp/servers": (200, SERVERS),
                "/mcp/oauth/connections": (503, {"detail": "down"}),
            }
        )
        found = list_servers(transport=transport)
        assert len(found) == 2

    def test_and_an_unknown_connection_is_not_reported_as_disconnected(self):
        transport = _Transport(
            {
                "/mcp/servers": (200, SERVERS),
                "/mcp/oauth/connections": (503, {"detail": "down"}),
            }
        )
        assert all(s.connected is None for s in list_servers(transport=transport))


class TestSkills:
    def _skills(self, payload=SKILLS, status=200):
        return list_skills(transport=_Transport({"/skills": (status, payload)}))

    def test_it_reports_each_skill(self):
        assert len(self._skills()) == 2

    def test_it_reports_the_name(self):
        assert self._skills()[0].name == "data-discovery"

    def test_it_reports_what_the_skill_is_for(self):
        assert "dataset" in self._skills()[0].description

    def test_a_refusal_is_not_an_empty_list(self):
        with pytest.raises(InventoryFailed):
            self._skills(status=403)

    def test_a_bare_list_is_read_too(self):
        assert len(self._skills(payload=SKILLS["skills"])) == 2
