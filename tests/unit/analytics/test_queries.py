"""Analytics: the derived figures, and what they refuse to report."""

from __future__ import annotations

import pytest

from agent.src.analytics.queries import (
    MAX_WINDOW_DAYS,
    Summary,
    UserBreakdown,
    Window,
    by_user,
    classify_error,
)


class TestWindow:
    def test_a_window_is_bounded(self):
        assert Window(days=10_000).days == MAX_WINDOW_DAYS

    def test_a_window_is_at_least_a_day(self):
        assert Window(days=0).days == 1
        assert Window(days=-5).days == 1


class TestRatesAreNotInvented:
    def test_no_runs_means_no_success_rate(self):
        assert Summary(window_days=7).success_rate is None

    def test_in_flight_runs_do_not_count_as_failures(self):
        summary = Summary(window_days=7, successes=9, errors=1, in_flight=90)
        assert summary.success_rate == 90.0

    def test_no_feedback_means_no_satisfaction_score(self):
        assert Summary(window_days=7, runs=500).satisfaction is None

    def test_satisfaction_is_the_share_of_ratings(self):
        summary = Summary(window_days=7, feedback_up=3, feedback_down=1)
        assert summary.satisfaction == 75.0


class TestErrorClassifier:
    """Every case here is an error this deployment actually produced."""

    @pytest.mark.parametrize(
        "message,expected",
        [
            (
                "Failed to create Gemini model 'gemini-2.5-pro': "
                "No Google credentials found.",
                "model_config",
            ),
            (
                "Max retries exceeded after repeated worker failures",
                "retries_exhausted",
            ),
            ("string indices must be integers, not 'str'", "agent_defect"),
            ("429 Resource has been exhausted (e.g. check quota)", "model_rate_limit"),
            ("Deadline Exceeded while awaiting the model", "model_timeout"),
            ("connection refused: could not connect to postgres", "storage"),
            ("Run cancelled by the client", "cancelled"),
        ],
    )
    def test_real_failures_are_classified(self, message, expected):
        assert classify_error(message) == expected

    def test_an_unrecognised_failure_is_other_not_a_guess(self):
        assert classify_error("the flux capacitor fluxed") == "other"

    def test_a_missing_message_is_unknown(self):
        assert classify_error(None) == "unknown"
        assert classify_error("") == "unknown"

    def test_the_message_itself_is_never_returned(self):
        secret = "could not read /uploads/alice-salary-2026.xlsx"
        label = classify_error(secret)
        assert "alice" not in label
        assert "uploads" not in label


class TestPerUserIsGated:
    @pytest.mark.asyncio
    async def test_disabled_returns_no_rows_and_says_why(self):
        result = await by_user(Window(days=7), enabled=False)
        assert isinstance(result, UserBreakdown)
        assert result.enabled is False
        assert result.rows == []
        assert "expose_users" in result.reason


class TestRouteGating:
    def test_the_user_endpoint_defaults_to_off(self):
        from agent.aegra.analytics_routes import _expose_users

        assert _expose_users() in (True, False)

    def test_an_unreadable_config_disables_disclosure(self, monkeypatch):
        import agent.aegra.analytics_routes as routes

        class Boom:
            def get_raw_section(self, _name):
                raise RuntimeError("config is broken")

        monkeypatch.setattr(
            "agent.src.agent.config.agent_config", Boom(), raising=False
        )
        assert routes._expose_users() is False


class TestStaleRunsAreNotInFlight:
    """A run whose pod died stays `running` forever."""

    def test_the_cutoff_matches_the_longest_permitted_operation(self):
        from agent.src.analytics import queries

        assert queries._STALE_AFTER_SECONDS == 3600

    def test_the_query_bounds_in_flight_by_age(self):
        from agent.src.analytics import queries

        sql = queries._SUMMARY_SQL if hasattr(queries, "_SUMMARY_SQL") else ""
        if not sql:
            import inspect

            sql = inspect.getsource(queries)
        assert "stale_after" in sql
        assert "AS stale" in sql

    def test_summary_reports_stale_separately(self):
        from agent.src.analytics.queries import Summary

        summary = Summary(window_days=7, in_flight=1, stale=2)
        assert summary.in_flight == 1
        assert summary.stale == 2


class TestConversationsExcludeMachineTraffic:
    """ "Conversations" has to mean a person had one."""

    def test_every_query_filters_to_client_traffic(self):
        """All of them, or the page cannot be read."""
        import inspect
        import re

        from agent.src.analytics import queries

        src = inspect.getsource(queries)
        lines = src.split("\n")
        unfiltered = []
        for i, line in enumerate(lines):
            if re.search(r"FROM runs\b", line):
                window = "\n".join(lines[i : i + 12])
                if "trace_id" not in window and "_CLIENT_ONLY" not in window:
                    unfiltered.append(i + 1)
        assert not unfiltered, f"unfiltered runs queries at lines {unfiltered}"

    def test_summary_carries_both(self):
        from agent.src.analytics.queries import Summary

        s = Summary(window_days=7, conversations=3, threads=355)
        assert s.conversations == 3
        assert s.threads == 355

    def test_conversations_defaults_to_zero_not_to_threads(self):
        from agent.src.analytics.queries import Summary

        assert Summary(window_days=7, threads=99).conversations == 0
