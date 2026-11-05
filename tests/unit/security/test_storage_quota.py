"""How much a team may keep, and what happens as it fills up."""

from __future__ import annotations

import pytest

from agent.src.security.storage_quota import Quota, State, check_storage


def quota(**kwargs) -> Quota:
    defaults = {
        "used_bytes": 1_000_000,
        "limit_bytes": 10_000_000,
        "incoming_bytes": 0,
        "oldest_removable_bytes": 0,
    }
    defaults.update(kwargs)
    return Quota(**defaults)


def test_plenty_of_room_is_fine():
    assert check_storage(quota()).state is State.FINE


def test_what_is_left_is_reported():
    assert check_storage(quota()).remaining_bytes == 9_000_000


def test_a_nearly_full_store_is_warned_about():
    assert check_storage(quota(used_bytes=8_500_000)).state is State.NEARLY_FULL


def test_a_full_store_is_reported_as_full():
    assert check_storage(quota(used_bytes=10_000_000)).state is State.FULL


def test_an_upload_that_fits_is_allowed():
    assert check_storage(quota(incoming_bytes=500_000)).may_accept is True


def test_an_upload_that_would_not_fit_is_refused():
    tight = quota(used_bytes=9_900_000, incoming_bytes=500_000)
    assert check_storage(tight).may_accept is False


def test_an_upload_that_fits_exactly_is_allowed():
    exact = quota(used_bytes=9_500_000, incoming_bytes=500_000)
    assert check_storage(exact).may_accept is True


def test_a_refused_upload_says_how_much_too_big_it_is():
    tight = quota(used_bytes=9_900_000, incoming_bytes=500_000)
    assert "400" in check_storage(tight).reason


def test_reading_is_never_stopped_by_a_full_store():
    assert check_storage(quota(used_bytes=10_000_000)).may_read is True


def test_deleting_is_never_stopped_by_a_full_store():
    assert check_storage(quota(used_bytes=10_000_000)).may_delete is True


def test_how_much_could_be_cleared_is_reported():
    with_old = quota(used_bytes=9_000_000, oldest_removable_bytes=2_000_000)
    assert check_storage(with_old).could_free_bytes == 2_000_000


def test_a_full_store_with_removable_data_suggests_clearing_it():
    with_old = quota(used_bytes=10_000_000, oldest_removable_bytes=2_000_000)
    assert "clear" in check_storage(with_old).reason


def test_a_full_store_with_nothing_removable_does_not_suggest_clearing():
    assert "clear" not in check_storage(quota(used_bytes=10_000_000)).reason


def test_the_share_used_is_reported():
    assert check_storage(quota(used_bytes=5_000_000)).share_used == 0.5


def test_a_store_over_its_limit_never_reports_more_than_full():
    assert check_storage(quota(used_bytes=12_000_000)).share_used == 1.0


def test_a_store_over_its_limit_has_nothing_left():
    assert check_storage(quota(used_bytes=12_000_000)).remaining_bytes == 0


def test_a_limit_of_nothing_is_refused():
    with pytest.raises(ValueError):
        quota(limit_bytes=0)


def test_negative_usage_is_refused():
    with pytest.raises(ValueError):
        quota(used_bytes=-1)
