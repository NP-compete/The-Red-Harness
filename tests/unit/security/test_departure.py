"""What happens to someone's work when they leave."""

from __future__ import annotations

from agent.src.knowledge.scopes import Collection, Scope
from agent.src.security.departure import plan_departure

LEAVER = "leaver@example.com"


def collections() -> list[Collection]:
    return [
        Collection(name="runbooks", scope=Scope.AGENT),
        Collection(name="sre-notes", scope=Scope.TEAM, team="sre"),
        Collection(name="my-uploads", scope=Scope.USER, owner=LEAVER),
        Collection(name="their-uploads", scope=Scope.USER, owner="other@example.com"),
    ]


def plan(**kwargs):
    defaults = {
        "subject": LEAVER,
        "collections": collections(),
        "connected_servers": ["tracker", "docs"],
        "granted_delegations": ["ticket-triage"],
    }
    defaults.update(kwargs)
    return plan_departure(**defaults)


def test_every_connection_is_revoked():
    assert plan().revoke_connections == ("docs", "tracker")


def test_grants_they_made_are_revoked_too():
    assert plan().revoke_delegations == ("ticket-triage",)


def test_agents_running_on_those_grants_are_stopped():
    assert plan().stop_agents == ("ticket-triage",)


def test_their_private_collections_are_listed_for_disposal():
    assert plan().personal_collections == ("my-uploads",)


def test_team_content_stays_where_it_is():
    assert "sre-notes" not in plan().personal_collections


def test_shared_agent_content_stays_too():
    assert "runbooks" not in plan().personal_collections


def test_somebody_else_private_content_is_untouched():
    assert "their-uploads" not in plan().personal_collections


def test_a_leaver_with_nothing_connected_still_plans_cleanly():
    p = plan(connected_servers=[], granted_delegations=[])
    assert p.revoke_connections == ()
    assert p.stop_agents == ()


def test_the_plan_names_the_person_it_is_for():
    assert plan().subject == LEAVER


def test_nothing_is_deleted_by_the_plan_itself():
    assert not any(
        hasattr(plan(), field) for field in ("deleted", "purged", "executed")
    )


def test_stopped_agents_are_reported_with_a_reason():
    assert "left" in plan().reason.lower()
