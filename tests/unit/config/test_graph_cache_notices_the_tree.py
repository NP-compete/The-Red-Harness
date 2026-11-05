"""A cached graph is retired when the configuration changes (CFG-6)."""

from __future__ import annotations

import pytest
from agent.aegra.graph import _graph_fingerprint
from agent.src.agent.config.loader import agent_config
from agent.src.agent.config.paths import config_root


def _key() -> str:
    return _graph_fingerprint(
        model_name="a-model",
        system_prompt="a prompt",
        tool_names=["one"],
        hitl_exclude=[],
        temperature=0.0,
        max_tokens=100,
        mcp_names=[],
        resource_uris=[],
        user_identity="somebody",
    )


@pytest.fixture
def tree_touched(tmp_path, monkeypatch):
    """Change a tree on disk, and put it back.

    A copy, pointed at with `CONFIG_PATH`. This used to edit the
    shipped `config/agent/runtime/agent.yaml` in place and restore
    it on teardown — which is fine until the run is interrupted,
    and then `# touched by a test` is left in the tree that ships.
    Teardown is not a guarantee; not writing there is.
    """
    import shutil

    copy = tmp_path / "agent"
    shutil.copytree(config_root(), copy)
    # Both: `CONFIG_PATH` is what `config_root()` reads, and
    # `_base_dir` is captured when the loader is constructed, so
    # the env var alone leaves the singleton reading the real tree.
    # `loader.py` compares the two, so they have to agree.
    monkeypatch.setenv("CONFIG_PATH", str(copy))
    monkeypatch.setattr(agent_config, "_base_dir", copy)

    path = copy / "runtime" / "agent.yaml"
    before = path.read_text()
    agent_config.get_name()
    yield lambda: path.write_text(before + "\n# touched by a test\n")
    path.write_text(before)
    agent_config.get_name()


class TestTheKeyFollowsTheTree:
    def test_it_is_stable_while_nothing_changes(self):
        agent_config.get_name()
        assert _key() == _key()

    def test_a_change_on_disk_moves_it(self, tree_touched):
        was = _key()
        tree_touched()
        agent_config.get_name()

        assert _key() != was, (
            "the configuration changed on disk, the loader re-read it, and "
            "the graph cache key did not move — so the cached graph built "
            "from the old tree is still what a request gets"
        )

    def test_an_edit_through_the_editor_moves_it(self, monkeypatch):
        from agent.aegra import config_editing_routes as routes
        from agent.src.agent.config import resolution

        monkeypatch.setenv(routes.STORE, "memory")
        routes.forget_overlay()
        resolution.use_overlay(None)
        try:
            agent_config.get_name()
            was = _key()
            store = routes._store()
            target = config_root() / "runtime" / "agent.yaml"
            key = resolution.overlay_key(target)
            assert key is not None
            store.apply(key, resolution.effective_text(target) + "\n", author="test")

            assert _key() != was
        finally:
            routes.forget_overlay()
            resolution.use_overlay(None)
            agent_config.get_name()


class TestTheLoaderCounter:
    def test_it_does_not_load(self):
        """Asking how current the tree is must not make it current."""
        agent_config.get_name()
        settled = agent_config.generation()
        for _ in range(5):
            agent_config.generation()
        assert agent_config.generation() == settled

    def test_it_moves_once_per_load(self, tree_touched):
        agent_config.get_name()
        was = agent_config.generation()
        tree_touched()
        agent_config.get_name()
        after = agent_config.generation()
        assert after == was + 1, (was, after)
        agent_config.get_name()
        assert agent_config.generation() == after, "an unchanged tree reloaded"
