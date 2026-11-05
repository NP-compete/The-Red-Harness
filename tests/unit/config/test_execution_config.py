"""What a run is allowed to actually do, and what happens when that"""

from __future__ import annotations

import pytest

from agent.src.agent.config.loader import AgentConfig, ExecutionConfigUnreadable

PROMPT = "---\nname: test\nmodel: gemini-2.5-flash\n---\nPrompt.\n"


def config_dir(tmp_path, agent_yaml: str):
    made = tmp_path / "agent"
    (made / "runtime").mkdir(parents=True)
    (made / "PROMPT.md").write_text(PROMPT)
    (made / "runtime" / "agent.yaml").write_text(agent_yaml)
    return made


@pytest.fixture(autouse=True)
def fresh():
    AgentConfig._instance = None
    yield
    AgentConfig._instance = None


class TestWhatIsConfigured:
    def test_saying_nothing_leaves_runs_live(self, tmp_path):
        made = config_dir(tmp_path, "name: test\n")
        assert AgentConfig(made).get_effects_mode() == "live"

    def test_a_dry_run_is_read_as_one(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n  effects: dry_run\n")
        assert AgentConfig(made).get_effects_mode() == "dry_run"

    def test_live_is_read_as_live(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n  effects: live\n")
        assert AgentConfig(made).get_effects_mode() == "live"


class TestWhatCannotBeRead:
    """Refused, not guessed. There is no safe direction to guess in:"""

    def test_a_misspelled_mode_stops_the_agent(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n  effects: dry-run\n")
        with pytest.raises(ExecutionConfigUnreadable):
            AgentConfig(made).get_effects_mode()

    def test_an_unrecognised_mode_stops_the_agent(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n  effects: whatever\n")
        with pytest.raises(ExecutionConfigUnreadable):
            AgentConfig(made).get_effects_mode()

    def test_a_block_of_the_wrong_shape_stops_the_agent(self, tmp_path):
        made = config_dir(tmp_path, "execution: 'live'\n")
        with pytest.raises(ExecutionConfigUnreadable):
            AgentConfig(made).get_effects_mode()

    def test_the_refusal_says_what_was_written(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n  effects: dry-run\n")
        with pytest.raises(ExecutionConfigUnreadable, match="dry-run"):
            AgentConfig(made).get_effects_mode()

    def test_the_refusal_names_what_it_could_have_been(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n  effects: dry-run\n")
        with pytest.raises(ExecutionConfigUnreadable) as error:
            AgentConfig(made).get_effects_mode()
        said = str(error.value)
        assert "live" in said and "dry_run" in said

    def test_an_empty_block_is_not_a_mistake(self, tmp_path):
        made = config_dir(tmp_path, "execution:\n")
        assert AgentConfig(made).get_effects_mode() == "live"


class TestTheWholeFileCannotBeRead:
    """`agent.yaml` carries approvals, providers, limits and what a"""

    def _broken(self, tmp_path):
        return config_dir(tmp_path, "middleware: [unclosed\n  nonsense: {{\n")

    def test_a_file_that_will_not_parse_stops_the_agent(self, tmp_path):
        from agent.src.agent.config.loader import AgentConfigUnreadable

        with pytest.raises(AgentConfigUnreadable):
            AgentConfig(self._broken(tmp_path)).get_effects_mode()

    def test_the_refusal_names_the_file(self, tmp_path):
        from agent.src.agent.config.loader import AgentConfigUnreadable

        with pytest.raises(AgentConfigUnreadable, match="agent.yaml"):
            AgentConfig(self._broken(tmp_path)).get_effects_mode()

    def test_the_refusal_says_what_was_wrong_with_it(self, tmp_path):
        from agent.src.agent.config.loader import AgentConfigUnreadable

        with pytest.raises(AgentConfigUnreadable) as error:
            AgentConfig(self._broken(tmp_path)).get_effects_mode()
        assert "line" in str(error.value)

    def test_no_file_at_all_still_runs_on_defaults(self, tmp_path):
        made = tmp_path / "agent"
        (made / "runtime").mkdir(parents=True)
        (made / "PROMPT.md").write_text(PROMPT)
        assert AgentConfig(made).get_effects_mode() == "live"

    def test_an_empty_file_is_not_a_mistake(self, tmp_path):
        assert AgentConfig(config_dir(tmp_path, "")).get_effects_mode() == "live"
