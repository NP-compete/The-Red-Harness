"""Which scopes a deployment keeps, and how retrieval is tuned."""

from __future__ import annotations

import pytest

from agent.src.knowledge.config import KnowledgeMisconfigured, read_knowledge
from agent.src.knowledge.scopes import Scope


class TestOffUntilAskedFor:
    def test_nothing_configured_is_off(self):
        assert read_knowledge({}).enabled is False

    def test_an_empty_block_is_off(self):
        assert read_knowledge({"knowledge": {}}).enabled is False

    def test_a_disabled_library_keeps_no_scopes(self):
        assert read_knowledge({"knowledge": {"enabled": False}}).scopes == ()


class TestWhichScopesAreKept:
    @staticmethod
    def _on(**scopes):
        return read_knowledge({"knowledge": {"enabled": True, "scopes": scopes or {}}})

    def test_every_kept_scope_by_default(self):
        from agent.src.knowledge.config import KEPT

        assert set(self._on().scopes) == set(KEPT)

    def test_one_turned_off_is_not_kept(self):
        assert Scope.USER not in self._on(session=True, user=False, agent=True).scopes

    def test_the_others_still_are(self):
        found = self._on(session=True, user=False, agent=True).scopes
        assert {Scope.SESSION, Scope.AGENT} <= set(found)

    def test_turning_them_all_off_is_the_same_as_off(self):
        from agent.src.knowledge.config import KEPT

        off = {scope.value: False for scope in KEPT}
        assert self._on(**off).enabled is False

    def test_a_scope_nobody_has_heard_of_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured, match="sesion"):
            read_knowledge({"knowledge": {"enabled": True, "scopes": {"sesion": True}}})


class TestTheOrderRetrievalTriesThem:
    def test_the_narrowest_first_by_default(self):
        from agent.src.knowledge.config import DEFAULT_ORDER

        found = read_knowledge({"knowledge": {"enabled": True}})
        assert found.order == DEFAULT_ORDER
        assert found.order[0] is Scope.SESSION
        assert found.order[-1] is Scope.AGENT

    def test_a_deployment_can_change_it(self):
        found = read_knowledge(
            {
                "knowledge": {
                    "enabled": True,
                    "retrieval": {"default_order": ["agent", "session"]},
                }
            }
        )
        assert found.order == (Scope.AGENT, Scope.SESSION)

    def test_a_scope_that_is_off_is_dropped_from_the_order(self):
        found = read_knowledge(
            {
                "knowledge": {
                    "enabled": True,
                    "scopes": {"session": True, "user": False, "agent": True},
                    "retrieval": {"default_order": ["session", "user", "agent"]},
                }
            }
        )
        assert Scope.USER not in found.order

    def test_an_unknown_scope_in_the_order_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured):
            read_knowledge(
                {
                    "knowledge": {
                        "enabled": True,
                        "retrieval": {"default_order": ["everything"]},
                    }
                }
            )


class TestRetrievalSettings:
    @staticmethod
    def _with(**retrieval):
        return read_knowledge({"knowledge": {"enabled": True, "retrieval": retrieval}})

    def test_top_k_is_read(self):
        assert self._with(top_k=3).top_k == 3

    def test_a_top_k_of_nothing_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured, match="top_k"):
            self._with(top_k=0)

    def test_a_minimum_score_is_read(self):
        assert self._with(min_score=0.5).min_score == 0.5

    def test_a_minimum_score_outside_nought_to_one_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured, match="min_score"):
            self._with(min_score=1.5)


class TestLimits:
    def test_a_user_quota_is_read(self):
        found = read_knowledge(
            {"knowledge": {"enabled": True, "limits": {"user_max_bytes": 1024}}}
        )
        assert found.user_max_bytes == 1024

    def test_a_negative_quota_is_refused(self):
        with pytest.raises(KnowledgeMisconfigured):
            read_knowledge(
                {"knowledge": {"enabled": True, "limits": {"user_max_bytes": -1}}}
            )

    def test_a_quota_of_zero_is_allowed(self):
        found = read_knowledge(
            {"knowledge": {"enabled": True, "limits": {"user_max_bytes": 0}}}
        )
        assert found.user_max_bytes == 0


class TestTheShippedTree:
    def test_the_loader_reads_it(self):
        from agent.src.agent.config.loader import agent_config

        assert agent_config.get_knowledge_config() is not None

    def test_the_shipped_tree_ships_it_on_with_a_corpus(self):
        """It ships on: `config/agent/knowledge/` has documents in it.

        This asserted the opposite. The tree now carries a corpus and
        the deployed agent answers from it, so "ships off" described a
        tree that no longer exists. A library that is on and has
        nothing to read would be the worse state, so check both.
        """
        from pathlib import Path

        from agent.src.agent.config.loader import agent_config

        assert agent_config.get_knowledge_config().enabled is True
        corpus = Path(__file__).resolve().parents[3] / "config" / "agent" / "knowledge"
        assert any(corpus.glob("*.md")), f"library is on but {corpus} is empty"

    def test_the_shipped_tree_still_declares_all_three_scopes(self):
        import yaml

        from agent.src.agent.config.loader import agent_config

        raw = yaml.safe_load(
            (agent_config.base_dir / "runtime" / "agent.yaml").read_text()
        )
        from agent.src.knowledge.config import KEPT

        assert set(raw["knowledge"]["scopes"]) == {s.value for s in KEPT}


class TestTheTwoDocumentFeaturesStaySeparate:
    """Both exist on purpose and would be easy to merge wrongly."""

    @staticmethod
    def _doc():
        from pathlib import Path

        return Path(__file__).resolve().parents[3] / "docs" / "guides" / "documents.md"

    def test_the_difference_is_written_down(self):
        assert self._doc().is_file()

    def test_it_names_both(self):
        said = self._doc().read_text()
        assert "/documents" in said and "/knowledge/documents" in said

    def test_it_says_who_may_write_to_each(self):
        said = self._doc().read_text().lower()
        assert "privileged" in said and "quota" in said
