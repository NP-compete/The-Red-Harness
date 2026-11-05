"""`ok: 0 runs persisted` was hiding a statement that always raised (REL-2)."""

from __future__ import annotations

import pytest

from agent.aegra import shutdown


class TestTheSummaryCanSayItFailed:
    @pytest.fixture
    def pretend(self, monkeypatch):
        def set_up(active: int, persisted: int):
            from agent.aegra import lifecycle

            monkeypatch.setattr(
                lifecycle,
                "_get_active_runs",
                lambda: {f"r{n}": n for n in range(active)},
            )
            monkeypatch.setattr(lifecycle, "persist_inflight_runs", lambda: persisted)

        return set_up

    def test_a_run_that_was_not_persisted_is_an_error(self, pretend):
        pretend(active=1, persisted=0)
        said = shutdown._persist_inflight_runs()
        assert said.startswith("error:"), said
        assert "0/1" in said

    def test_nothing_in_flight_is_still_ok(self, pretend):
        pretend(active=0, persisted=0)
        assert shutdown._persist_inflight_runs() == "ok: 0 runs persisted"

    def test_all_of_them_is_ok(self, pretend):
        pretend(active=2, persisted=2)
        assert shutdown._persist_inflight_runs() == "ok: 2 runs persisted"

    def test_a_partial_failure_is_an_error_too(self, pretend):
        pretend(active=3, persisted=1)
        said = shutdown._persist_inflight_runs()
        assert said.startswith("error:") and "1/3" in said


class TestTheStatementCanBeTyped:
    def test_the_pod_id_is_cast(self):
        """The fix itself, pinned where it is readable."""
        import inspect

        from agent.aegra import lifecycle

        source = inspect.getsource(lifecycle._expire_run_leases_batch)
        assert "'started_by_pod', %s::text" in source, (
            "the pod id is passed to jsonb_build_object untyped again; "
            "Postgres cannot infer it and the whole UPDATE raises"
        )
