"""What may still be done while the connection is down."""

from __future__ import annotations

import pytest

from agent.src.agent.connection_state import Link, Want, decide_offline


def link(**kwargs) -> Link:
    defaults = {
        "connected": True,
        "seconds_down": 0,
        "queued": 0,
        "run_in_flight": False,
    }
    defaults.update(kwargs)
    return Link(**defaults)


def test_everything_is_allowed_while_connected():
    assert decide_offline(link(), want=Want("send")).allowed is True


def test_a_message_written_while_offline_is_queued():
    assert decide_offline(link(connected=False), want=Want("send")).queue is True


def test_a_queued_message_is_not_treated_as_sent():
    assert decide_offline(link(connected=False), want=Want("send")).allowed is False


def test_reading_what_is_already_loaded_still_works():
    assert decide_offline(link(connected=False), want=Want("read")).allowed is True


def test_searching_needs_the_connection():
    assert decide_offline(link(connected=False), want=Want("search")).allowed is False


def test_searching_is_not_queued_for_later():
    assert decide_offline(link(connected=False), want=Want("search")).queue is False


def test_something_that_cannot_be_undone_is_never_queued():
    assert decide_offline(link(connected=False), want=Want("delete")).queue is False


def test_something_that_cannot_be_undone_is_refused_outright():
    assert decide_offline(link(connected=False), want=Want("delete")).allowed is False


def test_a_refusal_says_why():
    assert decide_offline(link(connected=False), want=Want("delete")).reason


def test_an_allowed_want_needs_no_explanation():
    assert decide_offline(link(), want=Want("send")).reason == ""


def test_a_run_already_under_way_is_reported_as_uncertain():
    cut = link(connected=False, run_in_flight=True)
    assert decide_offline(cut, want=Want("read")).run_outcome_unknown is True


def test_no_run_under_way_means_no_uncertainty():
    assert (
        decide_offline(link(connected=False), want=Want("read")).run_outcome_unknown
        is False
    )


def test_a_brief_outage_is_not_worth_a_warning():
    assert (
        decide_offline(link(connected=False, seconds_down=2), want=Want("read")).warn
        is False
    )


def test_an_outage_that_lasts_is_worth_a_warning():
    assert (
        decide_offline(link(connected=False, seconds_down=30), want=Want("read")).warn
        is True
    )


def test_a_connected_link_never_warns():
    assert decide_offline(link(seconds_down=0), want=Want("read")).warn is False


def test_how_much_is_waiting_to_go_out_is_reported():
    waiting = link(connected=False, queued=3)
    assert decide_offline(waiting, want=Want("send")).queued == 4


def test_a_negative_outage_is_refused():
    with pytest.raises(ValueError):
        link(seconds_down=-1)
