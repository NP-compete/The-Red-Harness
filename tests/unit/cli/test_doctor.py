"""What is misconfigured, and what to do about it."""

from __future__ import annotations

import pytest

from agent.cli.doctor import DEGRADED_EXIT, Finding, Severity, diagnose


def _ok_world(**over):
    world = {
        "agent_reachable": True,
        "config_readable": True,
        "override_store": True,
        "model_key_present": True,
        "tracing_configured": True,
        "config_clean": True,
        "within_limits": True,
    }
    world.update(over)
    return world


def _by_name(findings: list[Finding]) -> dict[str, Finding]:
    return {f.name: f for f in findings}


class TestAHealthyDeployment:
    def test_has_nothing_to_report(self):
        assert diagnose(_ok_world()) == []


class TestTheAgentCannotBeReached:
    """The one that looks like everything else being broken."""

    def test_it_is_reported(self):
        found = _by_name(diagnose(_ok_world(agent_reachable=False)))
        assert "agent_reachable" in found

    def test_it_stops_the_tool_working_at_all(self):
        found = _by_name(diagnose(_ok_world(agent_reachable=False)))
        assert found["agent_reachable"].severity is Severity.BLOCKED

    def test_it_says_what_to_do(self):
        found = _by_name(diagnose(_ok_world(agent_reachable=False)))
        assert found["agent_reachable"].remedy


class TestTheConfigurationCannotBeRead:
    def test_it_is_reported_as_blocking(self):
        found = _by_name(diagnose(_ok_world(config_readable=False)))
        assert found["config_readable"].severity is Severity.BLOCKED


class TestNoModelKey:
    def test_it_is_reported_as_blocking(self):
        found = _by_name(diagnose(_ok_world(model_key_present=False)))
        assert found["model_key_present"].severity is Severity.BLOCKED


class TestNoOverrideStore:
    """Degraded, not broken, and the difference matters."""

    def test_it_is_reported(self):
        found = _by_name(diagnose(_ok_world(override_store=False)))
        assert "override_store" in found

    def test_it_does_not_claim_the_deployment_is_down(self):
        found = _by_name(diagnose(_ok_world(override_store=False)))
        assert found["override_store"].severity is Severity.DEGRADED

    def test_it_says_what_stops_working(self):
        found = _by_name(diagnose(_ok_world(override_store=False)))
        assert "capabilit" in found["override_store"].detail.lower()


class TestNoTracing:
    def test_it_is_only_a_note(self):
        found = _by_name(diagnose(_ok_world(tracing_configured=False)))
        assert found["tracing_configured"].severity is Severity.NOTE


class TestSeveralAtOnce:
    def test_every_one_is_reported(self):
        found = diagnose(_ok_world(agent_reachable=False, model_key_present=False))
        assert len(found) == 2

    def test_the_blocking_ones_come_first(self):
        found = diagnose(
            _ok_world(
                agent_reachable=False, tracing_configured=False, override_store=False
            )
        )
        assert [f.severity for f in found] == [
            Severity.BLOCKED,
            Severity.DEGRADED,
            Severity.NOTE,
        ]


class TestTheExitCode:
    @staticmethod
    def _code(findings):
        from agent.cli.doctor import exit_code

        return exit_code(findings)

    def test_nothing_wrong_is_success(self):
        assert self._code([]) == 0

    def test_something_blocking_is_a_failure(self):
        assert self._code(diagnose(_ok_world(agent_reachable=False))) == 1

    def test_something_degraded_is_a_different_failure(self):
        assert self._code(diagnose(_ok_world(override_store=False))) == DEGRADED_EXIT

    def test_a_note_alone_is_still_success(self):
        assert self._code(diagnose(_ok_world(tracing_configured=False))) == 0

    def test_the_worst_one_decides(self):
        findings = diagnose(_ok_world(agent_reachable=False, override_store=False))
        assert self._code(findings) == 1


class TestTheMachineReadableForm:
    def test_every_finding_carries_its_name(self):
        from agent.cli.doctor import as_json

        said = as_json(diagnose(_ok_world(agent_reachable=False)))
        assert said["findings"][0]["name"] == "agent_reachable"

    def test_it_carries_the_remedy_too(self):
        from agent.cli.doctor import as_json

        said = as_json(diagnose(_ok_world(agent_reachable=False)))
        assert said["findings"][0]["remedy"]

    def test_a_clean_report_says_so_rather_than_being_empty(self):
        from agent.cli.doctor import as_json

        assert as_json([])["ok"] is True

    @pytest.mark.parametrize("key", ["ok", "findings"])
    def test_the_shape_is_stable(self, key):
        from agent.cli.doctor import as_json

        assert key in as_json([])


class TestConfigurationThatLoadedWithProblems:
    """Running, but not with the configuration somebody wrote."""

    def test_it_is_reported(self):
        found = _by_name(diagnose(_ok_world(config_clean=False)))
        assert "config_clean" in found

    def test_it_does_not_claim_the_deployment_is_down(self):
        found = _by_name(diagnose(_ok_world(config_clean=False)))
        assert found["config_clean"].severity is Severity.DEGRADED

    def test_it_says_where_to_look(self):
        found = _by_name(diagnose(_ok_world(config_clean=False)))
        assert "config" in found["config_clean"].remedy.lower()

    def test_a_clean_load_says_nothing(self):
        assert _by_name(diagnose(_ok_world(config_clean=True))) == {}

    def test_an_older_agent_that_cannot_say_is_not_accused(self):
        world = _ok_world()
        world.pop("config_clean", None)
        assert "config_clean" not in _by_name(diagnose(world))


class TestSomethingOverALimit:
    """The dashboard answer, without opening the dashboard."""

    def test_it_is_reported(self):
        found = _by_name(diagnose(_ok_world(within_limits=False)))
        assert "within_limits" in found

    def test_it_does_not_claim_the_deployment_is_down(self):
        found = _by_name(diagnose(_ok_world(within_limits=False)))
        assert found["within_limits"].severity is Severity.DEGRADED

    def test_it_points_at_where_the_detail_is(self):
        found = _by_name(diagnose(_ok_world(within_limits=False)))
        assert "limit" in found["within_limits"].remedy.lower()

    def test_a_deployment_inside_its_limits_says_nothing(self):
        assert _by_name(diagnose(_ok_world(within_limits=True))) == {}

    def test_an_agent_that_cannot_say_is_not_accused(self):
        world = _ok_world()
        world.pop("within_limits", None)
        assert "within_limits" not in _by_name(diagnose(world))


class TestTheProbeForLimits:
    def test_a_healthy_window_reads_as_within(self):
        from unittest.mock import patch

        from agent.cli.probes import within_limits

        with patch("agent.cli.probes._get", return_value=(200, {"ok": True})):
            assert within_limits("http://x") is True

    def test_a_breach_reads_as_over(self):
        from unittest.mock import patch

        from agent.cli.probes import within_limits

        with patch("agent.cli.probes._get", return_value=(200, {"ok": False})):
            assert within_limits("http://x") is False

    def test_an_agent_that_cannot_answer_says_nothing(self):
        from unittest.mock import patch

        from agent.cli.probes import within_limits

        with patch("agent.cli.probes._get", return_value=(404, {})):
            assert within_limits("http://x") is None
