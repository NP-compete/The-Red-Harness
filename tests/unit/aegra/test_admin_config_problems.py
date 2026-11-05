"""The operator's view of a configuration that did not load cleanly."""

from __future__ import annotations

from unittest.mock import patch

from agent.src.agent.config.problems import note_problem, reset_problems


def _reported():
    from agent.aegra.admin_routes import config_problems

    return config_problems()


class TestWhatIsReported:
    def setup_method(self):
        reset_problems()

    def teardown_method(self):
        reset_problems()

    def test_a_clean_load_says_so(self):
        assert _reported()["clean"] is True

    def test_and_lists_nothing(self):
        assert _reported()["problems"] == []

    def test_a_problem_makes_it_not_clean(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert _reported()["clean"] is False

    def test_the_problem_is_listed(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert _reported()["problems"][0]["detail"] == "duplicate key 'model'"

    def test_it_names_the_file(self):
        note_problem("runtime/agent.yaml", "duplicate key 'model'")
        assert _reported()["problems"][0]["source"] == "runtime/agent.yaml"

    def test_clean_is_stated_rather_than_implied_by_an_empty_list(self):
        assert "clean" in _reported()


class TestTheProbeReadsIt:
    def test_a_clean_report_is_read_as_clean(self):
        from agent.cli.probes import config_clean

        with patch("agent.cli.probes._get", return_value=(200, {"clean": True})):
            assert config_clean("http://x") is True

    def test_problems_are_read_as_not_clean(self):
        from agent.cli.probes import config_clean

        with patch("agent.cli.probes._get", return_value=(200, {"clean": False})):
            assert config_clean("http://x") is False

    def test_an_agent_that_cannot_answer_is_not_accused(self):
        from agent.cli.probes import config_clean

        with patch("agent.cli.probes._get", return_value=(404, {})):
            assert config_clean("http://x") is None

    def test_an_unreachable_agent_is_not_accused_either(self):
        from agent.cli.probes import config_clean

        with patch("agent.cli.probes._get", side_effect=OSError("down")):
            assert config_clean("http://x") is None
