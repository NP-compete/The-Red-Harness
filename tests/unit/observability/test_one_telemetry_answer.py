"""Two OTEL bootstraps cannot disagree about telemetry (OBS-2, CFG-1)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent.src.observability import otel_setup


class Noisy:
    """A logger that remembers, so a stand-down is visible."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def info(self, message: str, *args, **kw) -> None:
        self.said.append(message)

    warning = info
    debug = info
    error = info


def _settings(**over):
    base = {
        "ENABLE_OTEL_METRICS": True,
        "ENABLE_OTEL_TRACES": True,
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317",
        "OTEL_SERVICE_NAME": "template-agent",
        "OTEL_METRIC_EXPORT_INTERVAL_MILLIS": 60000,
        "resolved_otel_traces_endpoint": lambda: "http://collector:4317",
        "otel_traces_active": lambda: True,
    }
    return SimpleNamespace(**{**base, **over})


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(otel_setup, "_metrics_initialized", False)
    monkeypatch.setattr(otel_setup, "_traces_initialized", False)
    monkeypatch.setattr(otel_setup, "_fastapi_instrumented", False)


class TestWhenTheConfiguredBootstrapIsUp:
    def test_metrics_stand_down(self, monkeypatch):
        monkeypatch.setattr(otel_setup, "_already_up", lambda: True)
        log = Noisy()

        otel_setup.setup_otel_metrics(_settings(), log)

        assert "template_agent_otel_metrics_already_configured" in log.said
        assert otel_setup._metrics_initialized is True

    def test_traces_stand_down(self, monkeypatch):
        monkeypatch.setattr(otel_setup, "_already_up", lambda: True)
        log = Noisy()

        otel_setup.setup_otel_traces(MagicMock(), _settings(), log)

        assert "template_agent_otel_traces_already_configured" in log.said
        assert otel_setup._traces_initialized is True

    def test_it_does_not_replace_the_meter_provider(self, monkeypatch):
        """The failure this prevents, named."""
        from opentelemetry import metrics

        monkeypatch.setattr(otel_setup, "_already_up", lambda: True)
        replaced = []
        monkeypatch.setattr(metrics, "set_meter_provider", replaced.append)

        otel_setup.setup_otel_metrics(_settings(), Noisy())

        assert replaced == []


class TestWhenItIsNot:
    def test_the_env_only_pair_still_works(self, monkeypatch):
        """A deployment configured only this way is not broken."""
        monkeypatch.setattr(otel_setup, "_already_up", lambda: False)
        from opentelemetry import metrics

        set_to = []
        monkeypatch.setattr(metrics, "set_meter_provider", set_to.append)

        otel_setup.setup_otel_metrics(_settings(), Noisy())

        assert set_to, "the environment-only path stopped setting up metrics"

    def test_and_off_is_still_off(self, monkeypatch):
        monkeypatch.setattr(otel_setup, "_already_up", lambda: False)
        from opentelemetry import metrics

        set_to = []
        monkeypatch.setattr(metrics, "set_meter_provider", set_to.append)

        otel_setup.setup_otel_metrics(_settings(ENABLE_OTEL_METRICS=False), Noisy())

        assert set_to == []


class TestTheQuestionItAsks:
    def test_an_unreachable_answer_is_not_already_up(self, monkeypatch):
        """Failing to ask must not mean "stand down"."""
        import builtins

        real = builtins.__import__

        def refuse(name, *args, **kw):
            if name == "agent.aegra":
                raise ImportError("no")
            return real(name, *args, **kw)

        monkeypatch.setattr(builtins, "__import__", refuse)
        assert otel_setup._already_up() is False

    def test_it_reflects_the_configured_bootstrap(self, monkeypatch):
        from agent.aegra import otel as configured

        monkeypatch.setattr(configured, "_initialized", True)
        monkeypatch.setattr(configured, "_otel_enabled", True)
        assert otel_setup._already_up() is True

        monkeypatch.setattr(configured, "_otel_enabled", False)
        assert otel_setup._already_up() is False
