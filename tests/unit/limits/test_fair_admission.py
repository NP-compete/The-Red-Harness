"""Who gets shed when the pod is full."""

from __future__ import annotations

import pytest

from agent.src.limits.fair_admission import FairShare


def _pod(capacity=10, **holding):
    share = FairShare(capacity=capacity)
    for caller, count in holding.items():
        for _ in range(count):
            share.took(caller)
    return share


class TestAnEmptyPod:
    def test_anybody_may_start(self):
        assert _pod().may_start("alice") is True

    def test_and_several(self):
        pod = _pod()
        for _ in range(5):
            assert pod.may_start("alice") is True
            pod.took("alice")


class TestOneCallerAlone:
    def test_they_may_use_the_whole_pod(self):
        pod = _pod(capacity=10, alice=9)
        assert pod.may_start("alice") is True

    def test_but_not_more_than_the_pod(self):
        pod = _pod(capacity=10, alice=10)
        assert pod.may_start("alice") is False


class TestTwoCallers:
    def test_each_may_hold_half(self):
        pod = _pod(capacity=10, alice=4, bea=1)
        assert pod.may_start("alice") is True

    def test_the_heavy_one_is_shed_at_their_share(self):
        pod = _pod(capacity=10, alice=5, bea=1)
        assert pod.may_start("alice") is False

    def test_while_the_light_one_still_gets_in(self):
        pod = _pod(capacity=10, alice=5, bea=1)
        assert pod.may_start("bea") is True

    def test_a_newcomer_counts_as_a_caller(self):
        pod = _pod(capacity=10, alice=9)
        assert pod.may_start("chen") is True


class TestWhenTheShareIsSmallerThanOne:
    def test_everybody_still_gets_one(self):
        pod = FairShare(capacity=2)
        for who in ("a", "b", "c"):
            pod.took(who)
        assert pod.may_start("d") is True


class TestFinishing:
    def test_a_finished_run_frees_the_slice(self):
        pod = _pod(capacity=10, alice=5, bea=1)
        assert pod.may_start("alice") is False
        pod.finished("alice")
        assert pod.may_start("alice") is True

    def test_a_caller_who_finishes_everything_stops_counting(self):
        pod = _pod(capacity=10, alice=1, bea=1)
        pod.finished("bea")
        assert pod.active_callers == 1

    def test_finishing_what_was_never_started_is_harmless(self):
        pod = _pod(capacity=10)
        pod.finished("nobody")
        assert pod.may_start("alice") is True

    def test_a_count_never_goes_below_nothing(self):
        pod = _pod(capacity=10, alice=1)
        pod.finished("alice")
        pod.finished("alice")
        assert pod.held_by("alice") == 0


class TestAnUnnamedCaller:
    def test_anonymity_does_not_buy_a_bigger_share(self):
        pod = _pod(capacity=10, bea=1, **{"": 5})
        assert pod.may_start("") is False

    def test_and_a_named_caller_is_not_crowded_out_by_them(self):
        pod = _pod(capacity=10, bea=1, **{"": 5})
        assert pod.may_start("bea") is True

    def test_alone_they_may_still_use_the_pod(self):
        pod = _pod(capacity=10, **{"": 5})
        assert pod.may_start("") is True


class TestNoCapacityConfigured:
    def test_nothing_is_shed(self):
        pod = FairShare(capacity=0)
        for _ in range(100):
            pod.took("alice")
        assert pod.may_start("alice") is True


@pytest.mark.parametrize("capacity", [1, 2, 10, 40])
def test_one_caller_never_takes_more_than_the_pod(capacity):
    pod = FairShare(capacity=capacity)
    admitted = 0
    for _ in range(capacity * 3):
        if pod.may_start("alice"):
            pod.took("alice")
            admitted += 1
    assert admitted == capacity


class TestTheDoorUsesIt:
    """Accounting nothing consults sheds nobody."""

    def test_admission_reaches_for_fair_share(self):
        import inspect

        from agent.aegra import admission

        assert "FairShare" in inspect.getsource(admission)

    def test_a_slice_is_given_back_however_the_run_ends(self):
        import inspect

        from agent.aegra import admission

        source = inspect.getsource(admission.AdmissionControlMiddleware)
        assert "finished" in source and "finally" in source
