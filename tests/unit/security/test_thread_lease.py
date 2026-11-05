"""One run at a time in a shared conversation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.src.security.thread_lease import ThreadLeases

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def leases(now=NOW, ttl_seconds=300) -> ThreadLeases:
    clock = {"now": now}
    store = ThreadLeases(now=lambda: clock["now"], ttl_seconds=ttl_seconds)
    store.advance = lambda seconds: clock.__setitem__(
        "now", clock["now"] + timedelta(seconds=seconds)
    )
    return store


def test_a_quiet_thread_can_be_claimed():
    assert leases().claim(thread="t1", subject="a@example.com").granted is True


def test_a_second_person_cannot_claim_a_held_thread():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    assert store.claim(thread="t1", subject="b@example.com").granted is False


def test_a_refusal_names_who_is_running():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    assert store.claim(thread="t1", subject="b@example.com").held_by == "a@example.com"


def test_the_holder_can_claim_again():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    assert store.claim(thread="t1", subject="a@example.com").granted is True


def test_another_thread_is_unaffected():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    assert store.claim(thread="t2", subject="b@example.com").granted is True


def test_releasing_frees_the_thread():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    store.release(thread="t1", subject="a@example.com")
    assert store.claim(thread="t1", subject="b@example.com").granted is True


def test_somebody_else_cannot_release_your_run():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    store.release(thread="t1", subject="b@example.com")
    assert store.claim(thread="t1", subject="b@example.com").granted is False


def test_a_lease_expires_so_a_dead_pod_does_not_lock_a_thread_for_ever():
    store = leases(ttl_seconds=60)
    store.claim(thread="t1", subject="a@example.com")
    store.advance(61)
    assert store.claim(thread="t1", subject="b@example.com").granted is True


def test_a_live_lease_does_not_expire_early():
    store = leases(ttl_seconds=60)
    store.claim(thread="t1", subject="a@example.com")
    store.advance(59)
    assert store.claim(thread="t1", subject="b@example.com").granted is False


def test_who_is_present_is_visible_without_claiming():
    store = leases()
    store.claim(thread="t1", subject="a@example.com")
    assert store.holder(thread="t1") == "a@example.com"


def test_nobody_holds_a_quiet_thread():
    assert leases().holder(thread="t1") is None
