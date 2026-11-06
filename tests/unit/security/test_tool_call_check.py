"""The last look at a tool call before it is made."""

from __future__ import annotations

import pytest

from agent.src.security.tool_call_check import Fault, Preflight, check_call


def preflight(**kwargs) -> Preflight:
    defaults = {
        "tool": "send-email",
        "server_trusted": True,
        "shape_unchanged": True,
        "arguments_valid": True,
        "credential_available": True,
        "destination_allowed": True,
        "within_rate_limit": True,
        "within_concurrency": True,
        "argument_problem": "",
    }
    defaults.update(kwargs)
    return Preflight(**defaults)


def test_a_sound_call_goes_ahead():
    assert check_call(preflight()).permitted is True


def test_a_sound_call_has_no_faults():
    assert check_call(preflight()).faults == ()


def test_an_untrusted_server_stops_the_call():
    assert Fault.SERVER_UNTRUSTED in check_call(preflight(server_trusted=False)).faults


def test_a_changed_tool_shape_stops_the_call():
    found = preflight(shape_unchanged=False, shape_problem="ask gained path")
    assert Fault.SHAPE_CHANGED in check_call(found).faults


def test_bad_arguments_stop_the_call():
    bad = preflight(arguments_valid=False, argument_problem="missing to")
    assert Fault.BAD_ARGUMENTS in check_call(bad).faults


def test_a_missing_credential_stops_the_call():
    assert (
        Fault.NO_CREDENTIAL in check_call(preflight(credential_available=False)).faults
    )


def test_a_forbidden_destination_stops_the_call():
    assert (
        Fault.DESTINATION_BLOCKED
        in check_call(preflight(destination_allowed=False)).faults
    )


def test_being_over_the_rate_limit_stops_the_call():
    assert Fault.RATE_LIMITED in check_call(preflight(within_rate_limit=False)).faults


def test_too_many_calls_at_once_stops_the_call():
    assert (
        Fault.TOO_MANY_AT_ONCE in check_call(preflight(within_concurrency=False)).faults
    )


def test_the_server_is_checked_before_anything_it_told_us():
    both = preflight(
        server_trusted=False, shape_unchanged=False, shape_problem="ask gained path"
    )
    assert check_call(both).faults[0] is Fault.SERVER_UNTRUSTED


def test_every_fault_is_reported_not_just_the_first():
    both = preflight(
        arguments_valid=False, argument_problem="missing to", credential_available=False
    )
    assert len(check_call(both).faults) == 2


def test_a_waitable_fault_is_distinguished_from_a_broken_one():
    assert check_call(preflight(within_rate_limit=False)).retryable is True


def test_a_broken_call_is_not_worth_retrying():
    bad = preflight(arguments_valid=False, argument_problem="missing to")
    assert check_call(bad).retryable is False


def test_a_call_with_both_kinds_of_fault_is_not_worth_retrying():
    both = preflight(
        within_rate_limit=False, arguments_valid=False, argument_problem="missing to"
    )
    assert check_call(both).retryable is False


def test_the_argument_problem_is_carried_through_for_the_model_to_fix():
    detailed = preflight(arguments_valid=False, argument_problem="missing to")
    assert "missing to" in check_call(detailed).reason


def test_the_reason_names_the_tool():
    assert "send-email" in check_call(preflight(server_trusted=False)).reason


def test_a_sound_call_needs_no_reason():
    assert check_call(preflight()).reason == ""


def test_a_call_without_a_tool_is_refused():
    with pytest.raises(ValueError):
        preflight(tool="  ")


def test_claiming_bad_arguments_without_saying_why_is_refused():
    with pytest.raises(ValueError):
        Preflight(
            tool="x",
            server_trusted=True,
            shape_unchanged=True,
            arguments_valid=False,
            credential_available=True,
            destination_allowed=True,
            within_rate_limit=True,
            within_concurrency=True,
            argument_problem="",
        )


def test_the_shape_problem_is_carried_through():
    found = check_call(
        preflight(shape_unchanged=False, shape_problem="ask gained path")
    )
    assert "gained path" in found.reason


def test_a_changed_shape_must_say_what_changed():
    import pytest

    with pytest.raises(ValueError):
        preflight(shape_unchanged=False)
