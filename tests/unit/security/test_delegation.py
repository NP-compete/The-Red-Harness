"""What an unattended run is allowed to do on somebody's behalf."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.src.security.delegation import DelegatedAuthoritySource, Delegation
from agent.src.security.resolver import Identity, ToolCall

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)
SCHEDULER = Identity(subject="ticket-triage", delegated_by="someone@example.com")
PERSON = Identity(subject="someone@example.com")
CREATE = ToolCall(name="tracker.create_issue", server="tracker", writes=True)


def grant(**kwargs) -> Delegation:
    defaults = {
        "granter": "someone@example.com",
        "agent": "ticket-triage",
        "tools": ["tracker.*"],
        "servers": ["tracker"],
        "expires_at": NOW + timedelta(hours=1),
    }
    defaults.update(kwargs)
    return Delegation(**defaults)


class Base:
    def __init__(self, held: bool | None = True) -> None:
        self._held = held
        self.subjects: list[str] = []

    def holds(self, identity: Identity, call: ToolCall) -> bool | None:
        self.subjects.append(identity.subject)
        return self._held


def source(delegation=None, base=None) -> DelegatedAuthoritySource:
    return DelegatedAuthoritySource(
        base=base or Base(),
        delegations=[delegation] if delegation else [],
        now=lambda: NOW,
    )


def test_a_person_acting_for_themselves_is_unaffected():
    base = Base()
    assert source(base=base).holds(PERSON, CREATE) is True
    assert base.subjects == ["someone@example.com"]


def test_an_unattended_run_with_no_grant_holds_nothing():
    assert source().holds(SCHEDULER, CREATE) is False


def test_a_grant_in_scope_is_honoured():
    assert source(grant()).holds(SCHEDULER, CREATE) is True


def test_an_expired_grant_authorises_nothing():
    assert (
        source(grant(expires_at=NOW - timedelta(seconds=1))).holds(SCHEDULER, CREATE)
        is False
    )


def test_a_tool_outside_the_grant_is_refused():
    assert source(grant(tools=["tracker.search"])).holds(SCHEDULER, CREATE) is False


def test_a_server_outside_the_grant_is_refused():
    assert source(grant(servers=["docs"])).holds(SCHEDULER, CREATE) is False


def test_a_grant_for_another_agent_does_not_apply():
    assert source(grant(agent="someone-else")).holds(SCHEDULER, CREATE) is False


def test_a_grant_from_another_person_does_not_apply():
    assert source(grant(granter="other@example.com")).holds(SCHEDULER, CREATE) is False


def test_a_revoked_grant_authorises_nothing():
    assert source(grant(revoked=True)).holds(SCHEDULER, CREATE) is False


def test_the_credential_checked_is_the_granter_own():
    base = Base()
    source(grant(), base=base).holds(SCHEDULER, CREATE)
    assert base.subjects == ["someone@example.com"]


def test_a_grant_dies_with_the_granter_authority():
    assert source(grant(), base=Base(held=False)).holds(SCHEDULER, CREATE) is False


def test_an_unreachable_credential_store_is_still_unknown():
    assert source(grant(), base=Base(held=None)).holds(SCHEDULER, CREATE) is None
