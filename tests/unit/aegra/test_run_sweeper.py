"""Interrupted runs are re-checked after boot, not only at boot."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agent.aegra import startup as st
from agent.src.settings import settings


@pytest.fixture(autouse=True)
def _no_leftover_tasks():
    yield
    for task in list(st._BACKGROUND_TASKS):
        task.cancel()
    st._BACKGROUND_TASKS.clear()


class TestSweeperRegistration:
    def test_disabled_by_a_zero_interval(self):
        with patch.object(settings, "LIFECYCLE_SWEEP_INTERVAL_SECONDS", 0):
            assert st._start_interrupted_run_sweeper() == "skipped: sweep disabled"

    def test_disabled_with_lifecycle_persistence_off(self):
        with patch.object(settings, "LIFECYCLE_PERSISTENCE_ENABLED", False):
            result = st._start_interrupted_run_sweeper()
        assert "lifecycle persistence disabled" in result

    async def test_enabled_reports_its_cadence_and_holds_the_task(self):
        with (
            patch.object(settings, "LIFECYCLE_PERSISTENCE_ENABLED", True),
            patch.object(settings, "LIFECYCLE_SWEEP_INTERVAL_SECONDS", 30),
        ):
            result = st._start_interrupted_run_sweeper()
        assert result == "ok: every 30s"
        assert len(st._BACKGROUND_TASKS) == 1

    async def test_it_actually_rechecks(self):
        resume = AsyncMock(return_value="ok: 2 reset, 0 stale")
        with (
            patch.object(settings, "LIFECYCLE_PERSISTENCE_ENABLED", True),
            patch.object(settings, "LIFECYCLE_SWEEP_INTERVAL_SECONDS", 1),
            patch.object(settings, "LIFECYCLE_SWEEP_MIN_AGE_SECONDS", 45),
            patch.object(st, "_resume_interrupted_runs", resume),
        ):
            st._start_interrupted_run_sweeper()
            await asyncio.sleep(1.2)

        assert resume.await_count >= 1
        assert resume.await_args.kwargs == {
            "min_age_seconds": 45,
            "startup": False,
        }

    async def test_a_failing_sweep_does_not_kill_the_loop(self):
        calls = {"n": 0}

        async def flaky(**kwargs):
            calls["n"] += 1
            raise RuntimeError("database down")

        with (
            patch.object(settings, "LIFECYCLE_PERSISTENCE_ENABLED", True),
            patch.object(settings, "LIFECYCLE_SWEEP_INTERVAL_SECONDS", 1),
            patch.object(st, "_resume_interrupted_runs", flaky),
        ):
            st._start_interrupted_run_sweeper()
            await asyncio.sleep(2.2)

        assert calls["n"] >= 2
