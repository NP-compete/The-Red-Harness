"""Catching credentials before they leave the run."""

from __future__ import annotations

import pytest

from agent.src.security.secret_scan import Kind, scan

CLEAN = "Please summarise the quarterly numbers for the team."


def test_ordinary_text_holds_no_secrets():
    assert scan(CLEAN).findings == ()


def test_ordinary_text_may_be_sent():
    assert scan(CLEAN).safe_to_send is True


def test_a_private_key_block_is_caught():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK\n-----END RSA PRIVATE KEY-----"
    assert scan(text).findings[0].kind is Kind.PRIVATE_KEY


def test_any_private_key_block_is_caught():
    text = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNza\n-----END OPENSSH PRIVATE KEY-----"
    assert scan(text).findings[0].kind is Kind.PRIVATE_KEY


def test_a_bearer_token_is_caught():
    assert (
        scan("Authorization: Bearer sk-aFq82hdM10zXwQ7bT4lPmN").findings[0].kind
        is Kind.BEARER_TOKEN
    )


def test_a_password_assignment_is_caught():
    assert scan('password = "hunter2correct-horse"').findings[0].kind is Kind.PASSWORD


def test_an_api_key_assignment_is_caught():
    assert (
        scan("API_KEY=9f2b7c1e4a6d8035bb17c9e2f4a6d803").findings[0].kind
        is Kind.API_KEY
    )


def test_a_connection_string_with_a_password_is_caught():
    url = "postgres://app:s3cr3tpassword@db.example.com:5432/main"
    assert scan(url).findings[0].kind is Kind.CONNECTION_STRING


def test_a_connection_string_without_a_password_is_not_a_finding():
    assert scan("postgres://db.example.com:5432/main").findings == ()


def test_anything_found_blocks_the_send():
    assert scan("API_KEY=9f2b7c1e4a6d8035bb17c9e2f4a6d803").safe_to_send is False


def test_the_secret_itself_is_never_repeated_back():
    secret = "9f2b7c1e4a6d8035bb17c9e2f4a6d803"
    report = scan(f"API_KEY={secret}")
    assert secret not in report.findings[0].excerpt
    assert secret not in report.summary


def test_the_finding_says_where_in_the_text_it_was():
    report = scan("line one\nAPI_KEY=9f2b7c1e4a6d8035bb17c9e2f4a6d803\nline three")
    assert report.findings[0].line == 2


def test_a_placeholder_is_not_treated_as_a_secret():
    assert scan('password = "<your password here>"').findings == ()


@pytest.mark.parametrize("value", ["", "***", "REDACTED", "xxx"])
def test_an_obviously_empty_value_is_not_treated_as_a_secret(value):
    assert scan(f'password = "{value}"').findings == ()


def test_a_short_value_is_not_treated_as_a_key():
    assert scan("API_KEY=on").findings == ()


def test_several_secrets_are_all_reported():
    text = 'password = "hunter2correct-horse"\nAPI_KEY=9f2b7c1e4a6d8035bb17c9e2f4a6d803'
    assert len(scan(text).findings) == 2


def test_the_summary_counts_what_was_found():
    text = 'password = "hunter2correct-horse"\nAPI_KEY=9f2b7c1e4a6d8035bb17c9e2f4a6d803'
    assert "2" in scan(text).summary


def test_an_empty_text_is_safe():
    assert scan("").safe_to_send is True
