"""E9-T1. The user-mutation policy, asked of a real OPA."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration

OPA = "http://localhost:8181/v1/data/agent/authz/deny_reasons"


def _ask(actor: str, target: str, field_class: str) -> list[str]:
    body = {
        "input": {
            "current_intent": {
                "action": "user_mutation",
                "actor_role": actor,
                "target_role": target,
                "field_class": field_class,
            }
        }
    }
    response = httpx.post(OPA, json=body, timeout=10.0)
    response.raise_for_status()
    return response.json().get("result") or []


@pytest.fixture(scope="module", autouse=True)
def _opa_is_up():
    try:
        httpx.get("http://localhost:8181/health", timeout=5.0).raise_for_status()
    except Exception:  # noqa: BLE001
        pytest.skip("no OPA at :8181 — `podman compose up opa`")


@pytest.mark.parametrize(
    ("actor", "target", "field_class"),
    [
        ("owners", "users", "membership"),
        ("owners", "owners", "entitlement"),
        ("admins", "users", "membership"),
        ("admins", "builders", "entitlement"),
        ("admins", "admins", "profile"),
        ("builders", "users", "profile"),
    ],
)
def test_permitted(actor, target, field_class):
    assert _ask(actor, target, field_class) == []


@pytest.mark.parametrize(
    ("actor", "target", "field_class", "why"),
    [
        (
            "admins",
            "admins",
            "membership",
            "an admin granting a peer a membership is granting it to themselves "
            "one step removed",
        ),
        ("admins", "owners", "profile", "nothing reaches upward"),
        ("builders", "users", "membership", "builders hold no membership power"),
        ("builders", "builders", "profile", "not even sideways"),
        ("users", "users", "profile", "an ordinary user mutates nobody here"),
    ],
)
def test_refused(actor, target, field_class, why):
    reasons = _ask(actor, target, field_class)
    assert reasons, why
    assert field_class in reasons[0] and actor in reasons[0], (
        "the reason must name the actor and the class, or an operator "
        f"reading an audit line cannot tell what was refused: {reasons}"
    )


def test_an_unknown_field_class_is_refused():
    """Fail closed. A class the policy has never heard of is not a"""
    assert _ask("owners", "users", "something_new")


def test_an_unknown_actor_role_is_refused():
    assert _ask("contractors", "users", "profile")


def test_a_non_mutation_intent_is_not_judged_here():
    """The policy must not answer questions it was not asked."""
    body = {
        "input": {"current_intent": {"action": "llm_response", "agent_message": "hi"}}
    }
    response = httpx.post(OPA, json=body, timeout=10.0)
    response.raise_for_status()
    assert response.json().get("result", []) == []
