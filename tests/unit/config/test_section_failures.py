"""A section that cannot be read must not become its defaults."""

from __future__ import annotations

import pytest

from agent.src.agent.config.loader import AgentConfig, ConfigSectionUnreadable

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


class TestAttachments:
    def test_what_is_configured_is_read(self, tmp_path):
        made = config_dir(tmp_path, "attachments:\n  enabled: false\n")
        assert AgentConfig(made).get_attachments_config().enabled is False

    def test_saying_nothing_leaves_the_default(self, tmp_path):
        made = config_dir(tmp_path, "name: test\n")
        assert AgentConfig(made).get_attachments_config().enabled is True

    def test_an_unreadable_section_stops_the_agent(self, tmp_path):
        made = config_dir(tmp_path, "attachments:\n  max_file_bytes: enormous\n")
        with pytest.raises(ConfigSectionUnreadable):
            AgentConfig(made).get_attachments_config()

    def test_a_typo_does_not_switch_uploads_back_on(self, tmp_path):
        made = config_dir(
            tmp_path, "attachments:\n  enabled: false\n  max_file_bytes: enormous\n"
        )
        with pytest.raises(ConfigSectionUnreadable):
            AgentConfig(made).get_attachments_config()

    def test_a_typo_does_not_raise_the_size_ceiling(self, tmp_path):
        made = config_dir(
            tmp_path, "attachments:\n  max_file_bytes: 1024\n  mount_path: []\n"
        )
        with pytest.raises(ConfigSectionUnreadable):
            AgentConfig(made).get_attachments_config()

    def test_the_refusal_names_the_section(self, tmp_path):
        made = config_dir(tmp_path, "attachments:\n  max_file_bytes: enormous\n")
        with pytest.raises(ConfigSectionUnreadable, match="attachments"):
            AgentConfig(made).get_attachments_config()

    def test_the_refusal_says_what_was_wrong(self, tmp_path):
        made = config_dir(tmp_path, "attachments:\n  max_file_bytes: enormous\n")
        with pytest.raises(ConfigSectionUnreadable) as error:
            AgentConfig(made).get_attachments_config()
        assert "max_file_bytes" in str(error.value)


class TestExtraction:
    def test_saying_nothing_leaves_the_default(self, tmp_path):
        made = config_dir(tmp_path, "name: test\n")
        assert AgentConfig(made).get_extraction_config() is not None

    def test_an_unreadable_section_stops_the_agent(self, tmp_path):
        made = config_dir(tmp_path, "extraction:\n  engine: whatever\n")
        with pytest.raises(ConfigSectionUnreadable):
            AgentConfig(made).get_extraction_config()

    def test_the_refusal_names_the_section(self, tmp_path):
        made = config_dir(tmp_path, "extraction:\n  engine: whatever\n")
        with pytest.raises(ConfigSectionUnreadable, match="extraction"):
            AgentConfig(made).get_extraction_config()
