"""What is worth interrupting somebody about."""

from __future__ import annotations

from agent.src.analytics.thresholds import Thresholds, breaches

OK = {
    "runs": 1000,
    "errors": 10,
    "success_rate": 0.99,
    "p95_seconds": 20.0,
    "total_cost": "5.00",
    "complete": True,
}

LIMITS = Thresholds(
    error_rate=0.05,
    p95_seconds=60.0,
    spend=None,
)


class TestAHealthyWindow:
    def test_says_nothing(self):
        assert breaches(OK, LIMITS) == []


class TestTooManyErrors:
    def test_it_is_reported(self):
        found = breaches({**OK, "errors": 200}, LIMITS)
        assert [b.name for b in found] == ["error_rate"]

    def test_it_says_what_was_measured(self):
        found = breaches({**OK, "errors": 200}, LIMITS)
        assert "20" in found[0].detail

    def test_it_says_what_the_limit_was(self):
        found = breaches({**OK, "errors": 200}, LIMITS)
        assert "5" in found[0].detail

    def test_exactly_at_the_limit_is_not_a_breach(self):
        assert breaches({**OK, "runs": 100, "errors": 5}, LIMITS) == []

    def test_a_window_with_no_runs_cannot_breach_a_rate(self):
        assert breaches({**OK, "runs": 0, "errors": 0}, LIMITS) == []


class TestSlowerThanAgreed:
    def test_it_is_reported(self):
        found = breaches({**OK, "p95_seconds": 90.0}, LIMITS)
        assert [b.name for b in found] == ["p95_seconds"]

    def test_a_latency_nobody_measured_is_not_a_breach(self):
        assert breaches({**OK, "p95_seconds": None}, LIMITS) == []


class TestSpending:
    def test_nothing_is_said_when_no_ceiling_is_set(self):
        assert breaches({**OK, "total_cost": "9999"}, LIMITS) == []

    def test_over_the_ceiling_is_reported(self):
        limits = Thresholds(error_rate=0.05, p95_seconds=60.0, spend="100")
        found = breaches({**OK, "total_cost": "250.00"}, limits)
        assert [b.name for b in found] == ["spend"]

    def test_an_incomplete_total_still_counts_once_it_is_over(self):
        limits = Thresholds(error_rate=0.05, p95_seconds=60.0, spend="100")
        found = breaches({**OK, "total_cost": "250.00", "complete": False}, limits)
        assert [b.name for b in found] == ["spend"]

    def test_an_incomplete_total_under_the_ceiling_says_nothing_yet(self):
        limits = Thresholds(error_rate=0.05, p95_seconds=60.0, spend="100")
        assert breaches({**OK, "total_cost": "50.00", "complete": False}, limits) == []

    def test_nothing_priced_is_not_nothing_spent(self):
        limits = Thresholds(error_rate=0.05, p95_seconds=60.0, spend="100")
        assert breaches({**OK, "total_cost": None}, limits) == []


class TestSeveralAtOnce:
    def test_each_is_reported(self):
        found = breaches({**OK, "errors": 200, "p95_seconds": 90.0}, LIMITS)
        assert {b.name for b in found} == {"error_rate", "p95_seconds"}

    def test_every_one_says_what_to_look_at(self):
        found = breaches({**OK, "errors": 200, "p95_seconds": 90.0}, LIMITS)
        assert all(b.detail for b in found)


class TestNoThresholdsConfigured:
    def test_nothing_fires(self):
        quiet = Thresholds(error_rate=None, p95_seconds=None, spend=None)
        assert breaches({**OK, "errors": 900, "p95_seconds": 999.0}, quiet) == []


class TestReadingTheConfiguredLimits:
    @staticmethod
    def _read(raw):
        from agent.src.analytics.thresholds import from_config

        return from_config(raw)

    def test_a_deployment_that_said_nothing_gets_no_alerts(self):
        limits = self._read({})
        assert (limits.error_rate, limits.p95_seconds, limits.spend) == (
            None,
            None,
            None,
        )

    def test_an_error_rate_is_read(self):
        assert self._read({"alerts": {"error_rate": 0.1}}).error_rate == 0.1

    def test_a_latency_limit_is_read(self):
        assert self._read({"alerts": {"p95_seconds": 45}}).p95_seconds == 45.0

    def test_a_spend_ceiling_stays_a_string(self):
        assert self._read({"alerts": {"spend": "100.00"}}).spend == "100.00"

    def test_an_unreadable_limit_is_ignored_rather_than_guessed(self):
        assert self._read({"alerts": {"error_rate": "soon"}}).error_rate is None

    def test_a_negative_limit_is_ignored(self):
        assert self._read({"alerts": {"p95_seconds": -1}}).p95_seconds is None


class TestTheEndpoint:
    @staticmethod
    async def _alerts(window, limits):
        from unittest.mock import AsyncMock, patch

        from agent.aegra import analytics_routes as ar

        with (
            patch.object(ar, "_summary_for_alerts", new=AsyncMock(return_value=window)),
            patch.object(ar, "_alert_thresholds", return_value=limits),
        ):
            return await ar.analytics_alerts(days=7, _token="t")

    async def test_a_healthy_window_reports_none(self):
        body = await self._alerts(OK, LIMITS)
        assert body["breaches"] == []

    async def test_and_says_so_rather_than_being_empty(self):
        body = await self._alerts(OK, LIMITS)
        assert body["ok"] is True

    async def test_a_breach_is_reported(self):
        body = await self._alerts({**OK, "errors": 200}, LIMITS)
        assert body["breaches"][0]["name"] == "error_rate"

    async def test_and_it_is_not_called_ok(self):
        body = await self._alerts({**OK, "errors": 200}, LIMITS)
        assert body["ok"] is False

    async def test_it_says_which_limits_were_applied(self):
        body = await self._alerts(OK, LIMITS)
        assert body["thresholds"]["error_rate"] == 0.05


class TestTheLimitsComeFromTheRealFile:
    """A reader pointed at nothing is an alerting system that never fires."""

    def test_it_reads_the_observability_file(self, tmp_path, monkeypatch):
        from agent.aegra import analytics_routes as ar
        from agent.src.agent.config.loader import agent_config

        tree = tmp_path / "runtime"
        tree.mkdir()
        (tree / "observability.yaml").write_text("alerts:\n  error_rate: 0.2\n")
        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)

        assert ar._alert_thresholds().error_rate == 0.2

    def test_a_file_with_no_alerts_block_configures_none(self, tmp_path, monkeypatch):
        from agent.aegra import analytics_routes as ar
        from agent.src.agent.config.loader import agent_config

        tree = tmp_path / "runtime"
        tree.mkdir()
        (tree / "observability.yaml").write_text("otel:\n  enabled: false\n")
        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)

        assert ar._alert_thresholds().error_rate is None

    def test_a_missing_file_configures_none(self, tmp_path, monkeypatch):
        from agent.aegra import analytics_routes as ar
        from agent.src.agent.config.loader import agent_config

        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)
        assert ar._alert_thresholds().spend is None
