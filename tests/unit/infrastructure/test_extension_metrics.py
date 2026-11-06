"""What each extension costs, and how often it says no."""

from __future__ import annotations

import pytest

from agent.src.infrastructure.extension_metrics import ExtensionTiming


@pytest.fixture
def timing() -> ExtensionTiming:
    return ExtensionTiming()


class TestBeforeAnythingHasRun:
    def test_an_extension_nobody_called_has_no_figures(self, timing):
        assert timing.summary("pkg:Thing") is None

    def test_nothing_at_all_is_reported_at_the_start(self, timing):
        assert timing.all() == {}


class TestCountingCalls:
    def test_a_call_is_counted(self, timing):
        timing.record("pkg:Thing", seconds=0.01)
        assert timing.summary("pkg:Thing")["calls"] == 1

    def test_calls_add_up(self, timing):
        for _ in range(3):
            timing.record("pkg:Thing", seconds=0.01)
        assert timing.summary("pkg:Thing")["calls"] == 3

    def test_one_extension_does_not_count_another(self, timing):
        timing.record("pkg:A", seconds=0.01)
        timing.record("pkg:B", seconds=0.01)
        assert timing.summary("pkg:A")["calls"] == 1


class TestHowLongItTakes:
    def test_it_reports_the_slowest_call(self, timing):
        timing.record("pkg:Thing", seconds=0.01)
        timing.record("pkg:Thing", seconds=0.40)
        assert timing.summary("pkg:Thing")["slowest_ms"] == pytest.approx(400, rel=0.01)

    def test_it_reports_the_usual_call(self, timing):
        timing.record("pkg:Thing", seconds=0.02)
        timing.record("pkg:Thing", seconds=0.04)
        assert timing.summary("pkg:Thing")["average_ms"] == pytest.approx(30, rel=0.01)

    def test_a_refusal_still_took_time_and_is_timed(self, timing):
        timing.record("pkg:Thing", seconds=0.05, refused=True)
        assert timing.summary("pkg:Thing")["average_ms"] == pytest.approx(50, rel=0.01)


class TestHowOftenItSaysNo:
    def test_a_refusal_is_counted(self, timing):
        timing.record("pkg:Thing", seconds=0.01, refused=True)
        assert timing.summary("pkg:Thing")["refusals"] == 1

    def test_an_ordinary_call_is_not_a_refusal(self, timing):
        timing.record("pkg:Thing", seconds=0.01)
        assert timing.summary("pkg:Thing")["refusals"] == 0

    def test_the_rate_is_refusals_over_calls(self, timing):
        timing.record("pkg:Thing", seconds=0.01, refused=True)
        for _ in range(3):
            timing.record("pkg:Thing", seconds=0.01)
        assert timing.summary("pkg:Thing")["refusal_rate"] == pytest.approx(0.25)

    def test_an_extension_that_never_refuses_reports_a_rate_of_nothing(self, timing):
        timing.record("pkg:Thing", seconds=0.01)
        assert timing.summary("pkg:Thing")["refusal_rate"] == 0.0


class TestReportingAllOfThem:
    def test_every_extension_that_ran_is_listed(self, timing):
        timing.record("pkg:A", seconds=0.01)
        timing.record("pkg:B", seconds=0.01)
        assert set(timing.all()) == {"pkg:A", "pkg:B"}

    def test_each_carries_its_own_figures(self, timing):
        timing.record("pkg:A", seconds=0.01, refused=True)
        timing.record("pkg:B", seconds=0.01)
        assert timing.all()["pkg:A"]["refusals"] == 1
        assert timing.all()["pkg:B"]["refusals"] == 0


class TestItDoesNotGrowWithoutBound:
    def test_a_long_running_agent_keeps_a_window_not_a_history(self, timing):
        for index in range(5000):
            timing.record("pkg:Thing", seconds=0.001 * index)
        assert timing.summary("pkg:Thing")["calls"] == 5000
        assert len(timing._seen["pkg:Thing"]) <= ExtensionTiming.WINDOW


class _Simple:
    """An extension with one hook, as the thinnest real one would be."""

    def __init__(self) -> None:
        self.saw = []

    def before_model(self, state):
        self.saw.append(state)
        return "unchanged"


class _Async:
    async def awrap_model_call(self, request, handler):
        return "answered"


class _Refuses:
    def before_model(self, state):
        raise RuntimeError("not allowed here")


class _Bare:
    """Something declared as an extension that hooks nothing."""


class TestTimingAnExtensionInPlace:
    @pytest.fixture(autouse=True)
    def clean(self):
        from agent.src.infrastructure import extension_metrics

        extension_metrics.timing = ExtensionTiming()
        yield extension_metrics.timing

    @staticmethod
    def _wrap(made, path="pkg:Thing"):
        from agent.src.infrastructure.extension_metrics import timed_extension

        return timed_extension(made, path)

    def test_a_hook_that_runs_is_counted(self, clean):
        self._wrap(_Simple()).before_model({})
        assert clean.summary("pkg:Thing")["calls"] == 1

    def test_the_hook_still_does_what_it_did(self):
        made = _Simple()
        assert self._wrap(made).before_model({"a": 1}) == "unchanged"
        assert made.saw == [{"a": 1}]

    def test_a_hook_that_refuses_is_counted_as_a_refusal(self, clean):
        with pytest.raises(RuntimeError):
            self._wrap(_Refuses()).before_model({})
        assert clean.summary("pkg:Thing")["refusals"] == 1

    def test_a_refusal_is_still_raised_at_the_caller(self):
        with pytest.raises(RuntimeError, match="not allowed here"):
            self._wrap(_Refuses()).before_model({})

    @pytest.mark.asyncio
    async def test_an_async_hook_is_counted(self, clean):
        await self._wrap(_Async()).awrap_model_call(object(), None)
        assert clean.summary("pkg:Thing")["calls"] == 1

    @pytest.mark.asyncio
    async def test_an_async_hook_still_answers(self):
        assert await self._wrap(_Async()).awrap_model_call(object(), None) == "answered"

    def test_an_extension_that_hooks_nothing_is_left_as_it_is(self):
        made = _Bare()
        assert self._wrap(made) is made

    def test_hooks_it_never_had_are_not_invented(self):
        assert not hasattr(self._wrap(_Simple()), "awrap_tool_call")

    def test_each_extension_is_counted_under_its_own_name(self, clean):
        self._wrap(_Simple(), "pkg:A").before_model({})
        self._wrap(_Simple(), "pkg:B").before_model({})
        self._wrap(_Simple(), "pkg:B").before_model({})
        assert clean.summary("pkg:A")["calls"] == 1
        assert clean.summary("pkg:B")["calls"] == 2
