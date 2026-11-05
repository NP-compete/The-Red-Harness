"""Which stored credential a given tool call is allowed to use."""

from __future__ import annotations

import pytest

from agent.src.security.credential_binding import (
    Binding,
    Credential,
    Refusal,
    credential_for,
)

CREDENTIALS = (
    Credential(name="mail-token", scopes=("mail.send",), owner="ana", shared=False),
    Credential(
        name="deploy-key", scopes=("deploy.write",), owner="team:platform", shared=True
    ),
)

BINDINGS = (
    Binding(tool="send-email", credential="mail-token", required_scope="mail.send"),
    Binding(tool="deploy", credential="deploy-key", required_scope="deploy.write"),
)


def test_a_tool_gets_the_credential_bound_to_it():
    found = credential_for(
        "send-email", caller="ana", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.credential == "mail-token"


def test_a_tool_with_no_binding_gets_nothing():
    found = credential_for(
        "search", caller="ana", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.refusal is Refusal.NO_BINDING


def test_a_tool_with_no_binding_is_not_handed_a_nearby_credential():
    found = credential_for(
        "search", caller="ana", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.credential == ""


def test_a_binding_to_a_credential_that_does_not_exist_is_refused():
    bindings = (
        Binding(tool="send-email", credential="missing", required_scope="mail.send"),
    )
    found = credential_for(
        "send-email", caller="ana", bindings=bindings, credentials=CREDENTIALS
    )
    assert found.refusal is Refusal.NO_CREDENTIAL


def test_a_credential_lacking_the_required_scope_is_refused():
    bindings = (
        Binding(
            tool="send-email", credential="mail-token", required_scope="mail.admin"
        ),
    )
    found = credential_for(
        "send-email", caller="ana", bindings=bindings, credentials=CREDENTIALS
    )
    assert found.refusal is Refusal.SCOPE_MISSING


def test_a_missing_scope_is_named():
    bindings = (
        Binding(
            tool="send-email", credential="mail-token", required_scope="mail.admin"
        ),
    )
    found = credential_for(
        "send-email", caller="ana", bindings=bindings, credentials=CREDENTIALS
    )
    assert "mail.admin" in found.reason


def test_a_personal_credential_is_not_lent_to_someone_else():
    found = credential_for(
        "send-email", caller="bo", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.refusal is Refusal.NOT_YOURS


def test_a_personal_credential_refusal_does_not_name_the_owner():
    found = credential_for(
        "send-email", caller="bo", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert "ana" not in found.reason


def test_a_shared_credential_may_be_used_by_anyone_with_the_tool():
    found = credential_for(
        "deploy", caller="bo", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.credential == "deploy-key"


def test_the_scope_actually_used_is_reported():
    found = credential_for(
        "send-email", caller="ana", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.scope == "mail.send"


def test_nothing_is_reported_as_used_when_refused():
    found = credential_for(
        "search", caller="ana", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert found.scope == ""


def test_a_credential_is_never_returned_in_the_result():
    found = credential_for(
        "send-email", caller="ana", bindings=BINDINGS, credentials=CREDENTIALS
    )
    assert not hasattr(found, "secret")


def test_two_bindings_for_the_same_tool_are_refused():
    duplicated = (
        Binding(tool="send-email", credential="mail-token", required_scope="mail.send"),
        Binding(
            tool="send-email", credential="deploy-key", required_scope="deploy.write"
        ),
    )
    with pytest.raises(ValueError):
        credential_for(
            "send-email", caller="ana", bindings=duplicated, credentials=CREDENTIALS
        )


def test_a_binding_without_a_scope_is_refused():
    with pytest.raises(ValueError):
        Binding(tool="send-email", credential="mail-token", required_scope=" ")


def test_a_credential_with_no_scopes_grants_nothing():
    empty = (Credential(name="mail-token", scopes=(), owner="ana", shared=False),)
    found = credential_for(
        "send-email", caller="ana", bindings=BINDINGS, credentials=empty
    )
    assert found.refusal is Refusal.SCOPE_MISSING


def test_an_empty_caller_is_refused():
    with pytest.raises(ValueError):
        credential_for(
            "send-email", caller=" ", bindings=BINDINGS, credentials=CREDENTIALS
        )
