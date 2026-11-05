"""Turning a failure into something safe to show and useful to act on."""

from __future__ import annotations

import pytest

from agent.src.security.failure_message import Audience, explain

TRACEBACK = (
    'File "/opt/app/services/agent/src/tools/mail.py", line 88, in send\n'
    "    raise ConnectionError('getaddrinfo failed for smtp.internal:587')"
)


def test_a_person_is_told_what_happened_in_plain_words():
    shown = explain("TypeError", TRACEBACK, audience=Audience.PERSON)
    assert shown.message == "The mail step could not be completed."


def test_a_person_is_not_shown_the_traceback():
    shown = explain("ConnectionError", TRACEBACK, audience=Audience.PERSON)
    assert "agent" not in shown.message


def test_a_person_is_not_shown_internal_host_names():
    shown = explain("ConnectionError", TRACEBACK, audience=Audience.PERSON)
    assert "smtp.internal" not in shown.message


def test_a_person_is_not_shown_file_paths():
    shown = explain("ConnectionError", TRACEBACK, audience=Audience.PERSON)
    assert "/opt/app" not in shown.message


def test_an_operator_is_shown_the_detail():
    shown = explain("ConnectionError", TRACEBACK, audience=Audience.OPERATOR)
    assert "smtp.internal" in shown.detail


def test_a_person_is_given_no_detail_at_all():
    assert explain("ConnectionError", TRACEBACK, audience=Audience.PERSON).detail == ""


def test_a_reference_links_the_two_views():
    shown = explain("ConnectionError", TRACEBACK, audience=Audience.PERSON)
    assert shown.reference != ""


def test_the_same_failure_gets_the_same_reference():
    first = explain("ConnectionError", TRACEBACK, audience=Audience.PERSON)
    second = explain("ConnectionError", TRACEBACK, audience=Audience.OPERATOR)
    assert first.reference == second.reference


def test_a_different_failure_gets_a_different_reference():
    other = explain("ValueError", TRACEBACK, audience=Audience.PERSON)
    assert (
        other.reference
        != explain("ConnectionError", TRACEBACK, audience=Audience.PERSON).reference
    )


def test_the_person_is_told_whether_it_is_worth_trying_again():
    assert (
        explain("TimeoutError", TRACEBACK, audience=Audience.PERSON).retryable is True
    )


def test_a_programming_mistake_is_not_worth_trying_again():
    assert explain("TypeError", TRACEBACK, audience=Audience.PERSON).retryable is False


def test_a_retryable_failure_says_so_in_the_message():
    shown = explain("TimeoutError", TRACEBACK, audience=Audience.PERSON)
    assert "try again" in shown.message


def test_an_unrecognised_failure_is_still_safe_to_show():
    shown = explain(
        "WidgetExplosion", "at 0x7f3c in libwidget.so", audience=Audience.PERSON
    )
    assert "libwidget" not in shown.message


def test_an_unrecognised_failure_still_gets_a_reference():
    shown = explain("WidgetExplosion", "boom", audience=Audience.PERSON)
    assert shown.reference != ""


def test_an_unrecognised_failure_is_not_claimed_to_be_retryable():
    assert (
        explain("WidgetExplosion", "boom", audience=Audience.PERSON).retryable is False
    )


def test_a_failure_with_no_name_is_refused():
    with pytest.raises(ValueError):
        explain("  ", "boom", audience=Audience.PERSON)


def test_no_message_ever_blames_the_person():
    for name in ["TimeoutError", "TypeError", "WidgetExplosion", "ConnectionError"]:
        message = explain(name, TRACEBACK, audience=Audience.PERSON).message
        assert "you" not in message.lower()
