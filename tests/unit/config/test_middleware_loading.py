"""Loading the middleware section, whichever file it arrives in."""

from __future__ import annotations

from agent.src.agent.config.middleware import load_middleware_config

STANDALONE = """
defaults:
  human_approval:
    default_decision: deny
    exclude: [ls]
profiles:
  fast:
    excluded_tools: [browse]
"""

AGENT_FILE = """
model: something
middleware:
  human_approval:
    default_decision: deny
    exclude: [ls]
harness_profiles:
  fast:
    excluded_tools: [browse]
"""


def write(tmp_path, text, name="middleware.yaml"):
    path = tmp_path / name
    path.write_text(text)
    return path


def test_a_standalone_file_loads(tmp_path):
    config = load_middleware_config(write(tmp_path, STANDALONE))
    assert config.defaults.human_approval.default_decision == "deny"


def test_a_standalone_file_keeps_its_profiles(tmp_path):
    assert "fast" in load_middleware_config(write(tmp_path, STANDALONE)).profiles


def test_the_agent_file_shape_loads_too(tmp_path):
    config = load_middleware_config(write(tmp_path, AGENT_FILE, "agent.yaml"))
    assert config.defaults.human_approval.default_decision == "deny"


def test_the_agent_file_profiles_are_found(tmp_path):
    config = load_middleware_config(write(tmp_path, AGENT_FILE, "agent.yaml"))
    assert "fast" in config.profiles


def test_the_agent_file_exclusions_survive(tmp_path):
    config = load_middleware_config(write(tmp_path, AGENT_FILE, "agent.yaml"))
    assert config.defaults.human_approval.exclude == ["ls"]


def test_a_missing_file_falls_back_to_defaults(tmp_path):
    config = load_middleware_config(tmp_path / "nothing.yaml")
    assert config.defaults.human_approval.default_decision == "ask"


def test_an_empty_file_falls_back_to_defaults(tmp_path):
    config = load_middleware_config(write(tmp_path, ""))
    assert config.defaults.human_approval.default_decision == "ask"
