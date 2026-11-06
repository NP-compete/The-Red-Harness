"""The fence needs a sentence telling the model what it means."""

from __future__ import annotations

from unittest.mock import patch

from agent.src.self_knowledge.describe import build_self_description


def _said(**kwargs):
    kwargs.setdefault("connected", ["jira"])
    with patch(
        "agent.src.agent.config.loader.AgentConfig.get_middleware_config",
        side_effect=RuntimeError("not configured here"),
    ):
        return build_self_description(**kwargs).lower()


class TestTheStandingInstructionSaysIt:
    def test_it_mentions_what_comes_back_from_a_server(self):
        assert "tool" in _said() or "server" in _said()

    def test_it_says_that_text_is_data(self):
        assert "data" in _said()

    def test_it_says_not_to_follow_it(self):
        said = _said()
        assert (
            "not an instruction" in said or "never" in said or "do not follow" in said
        )

    def test_it_says_what_an_instruction_inside_means(self):
        said = _said()
        assert "hostile" in said or "report" in said or "say so" in said

    def test_it_names_the_marker_so_the_model_can_see_the_boundary(self):
        assert "external-content" in _said()


class TestItIsOneParagraph:
    def test_it_does_not_repeat_the_memory_wording(self):
        said = _said()
        assert "file data read from disk" not in said

    def test_the_rest_of_the_description_still_appears(self):
        assert "gpt-nowhere" in _said(model_name="gpt-nowhere")


class TestADeploymentThatReachesNothing:
    """No integrations, nothing to fence, nothing to say."""

    def test_the_paragraph_is_absent(self):
        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_middleware_config",
            side_effect=RuntimeError("not configured here"),
        ):
            assert "external-content" not in build_self_description()

    def test_an_integration_that_is_merely_unconnected_still_gets_it(self):
        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_middleware_config",
            side_effect=RuntimeError("not configured here"),
        ):
            found = build_self_description(unconnected=["jira"])
        assert "external-content" in found
