"""The store a deployment actually gets, and whether it is offered."""

from __future__ import annotations

from unittest.mock import patch

from agent.src.knowledge.config import Knowledge
from agent.src.knowledge.scopes import Scope


def _read(raw):
    from agent.src.knowledge.config import read_knowledge

    return read_knowledge(raw)


def _on(**limits):
    return {
        "knowledge": {
            "enabled": True,
            "scopes": {"user": True},
            "limits": limits,
        }
    }


class TestTheCapsComeFromConfiguration:
    def test_there_is_a_default(self):
        assert _read(_on()).artifact_max_bytes > 0

    def test_a_deployment_can_set_the_total(self):
        assert _read(_on(artifact_max_bytes=4096)).artifact_max_bytes == 4096

    def test_a_deployment_can_set_the_size_of_one(self):
        assert _read(_on(artifact_value_max_bytes=512)).artifact_value_max_bytes == 512

    def test_one_value_may_not_exceed_the_whole_allowance(self):
        import pytest

        from agent.src.knowledge.config import KnowledgeMisconfigured

        with pytest.raises(KnowledgeMisconfigured):
            _read(_on(artifact_max_bytes=100, artifact_value_max_bytes=500))

    def test_lowering_only_the_total_is_not_an_error(self):
        found = _read(_on(artifact_max_bytes=100))
        assert found.artifact_value_max_bytes == 100

    def test_a_negative_cap_is_refused(self):
        import pytest

        from agent.src.knowledge.config import KnowledgeMisconfigured

        with pytest.raises(KnowledgeMisconfigured):
            _read(_on(artifact_max_bytes=-1))


class TestTheStoreIsOnePerProcess:
    def test_asking_twice_gives_the_same_store(self):
        from agent.src.knowledge.artifacts import session_artifacts

        assert session_artifacts() is session_artifacts()

    def test_it_is_built_to_the_configured_caps(self):
        from agent.src.knowledge import artifacts

        artifacts._SESSION_ARTIFACTS = None
        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
            return_value=Knowledge(
                enabled=True,
                scopes=(Scope.USER,),
                artifact_max_bytes=4096,
                artifact_value_max_bytes=512,
            ),
        ):
            store = artifacts.session_artifacts()
        assert store._max_total == 4096 and store._max_value == 512
        artifacts._SESSION_ARTIFACTS = None


class TestTheGraphOffersThem:
    def test_they_are_built_where_the_library_is_on(self):
        from agent.aegra.graph import _artifact_tools

        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
            return_value=Knowledge(enabled=True, scopes=(Scope.USER,)),
        ):
            assert _artifact_tools()

    def test_nothing_is_offered_where_it_is_off(self):
        from agent.aegra.graph import _artifact_tools

        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
            return_value=Knowledge(enabled=False),
        ):
            assert _artifact_tools() == []

    def test_a_store_that_will_not_build_does_not_stop_the_graph(self):
        from agent.aegra.graph import _artifact_tools

        with patch(
            "agent.src.agent.config.loader.AgentConfig.get_knowledge_config",
            side_effect=RuntimeError("configuration is unreadable"),
        ):
            assert _artifact_tools() == []

    def test_the_graph_actually_collects_them(self):
        import inspect

        from agent.aegra import graph

        assert "_artifact_tools" in inspect.getsource(graph.agent)
