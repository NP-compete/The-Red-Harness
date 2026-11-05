"""Which written guidance applies to a conversation."""

from __future__ import annotations

import pytest

from agent.src.security.skill_scope import Skill, applicable


def skills() -> list[Skill]:
    return [
        Skill(name="incident-triage", scope="agent", owner=None, team=None),
        Skill(name="sre-habits", scope="team", owner=None, team="sre"),
        Skill(name="my-style", scope="user", owner="me@example.com", team=None),
        Skill(name="their-style", scope="user", owner="you@example.com", team=None),
    ]


def test_agent_guidance_applies_to_everybody():
    chosen = applicable(skills(), subject="me@example.com", teams=())
    assert "incident-triage" in [s.name for s in chosen]


def test_my_own_guidance_applies_to_me():
    chosen = applicable(skills(), subject="me@example.com", teams=())
    assert "my-style" in [s.name for s in chosen]


def test_somebody_else_guidance_does_not_apply_to_me():
    chosen = applicable(skills(), subject="me@example.com", teams=())
    assert "their-style" not in [s.name for s in chosen]


def test_team_guidance_applies_to_members():
    chosen = applicable(skills(), subject="me@example.com", teams=("sre",))
    assert "sre-habits" in [s.name for s in chosen]


def test_team_guidance_does_not_apply_to_outsiders():
    chosen = applicable(skills(), subject="me@example.com", teams=("finance",))
    assert "sre-habits" not in [s.name for s in chosen]


def test_guidance_is_ordered_broadest_first():
    chosen = applicable(skills(), subject="me@example.com", teams=("sre",))
    assert [s.scope for s in chosen] == ["agent", "team", "user"]


def test_a_user_skill_without_an_owner_applies_to_nobody():
    orphan = [Skill(name="orphan", scope="user", owner=None, team=None)]
    assert applicable(orphan, subject="me@example.com", teams=()) == ()


def test_a_team_skill_without_a_team_applies_to_nobody():
    orphan = [Skill(name="orphan", scope="team", owner=None, team=None)]
    assert applicable(orphan, subject="me@example.com", teams=("sre",)) == ()


def test_an_unknown_scope_is_refused_rather_than_assumed_safe():
    with pytest.raises(ValueError):
        Skill(name="odd", scope="everyone", owner=None, team=None)


def test_no_guidance_is_a_valid_answer():
    assert applicable([], subject="me@example.com", teams=()) == ()
