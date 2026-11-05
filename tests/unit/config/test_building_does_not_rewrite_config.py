"""Building the graph must not rewrite the configuration."""

from __future__ import annotations

from agent.src.infrastructure.subagents import _inherit_from_orchestrator


class TestInheritanceLeavesTheDeclarationAlone:
    def test_it_does_not_write_into_what_it_is_given(self):
        working = {"model": "a-model"}
        _inherit_from_orchestrator(working, {"model": "parent-model"}, "sub")
        assert working["model"] != "a-model", (
            "inheritance is expected to enrich the copy it is given"
        )

    def test_the_cache_a_route_reads_is_not_the_one_built_from(self):
        from copy import deepcopy

        cached = {"sub": {"model": "a-model", "mcps": ["one"]}}
        before = deepcopy(cached)

        for _name, declared in cached.items():
            agent_cfg = deepcopy(declared)
            _inherit_from_orchestrator(agent_cfg, {"model": "parent-model"}, "sub")

        assert cached == before, (
            "building the graph rewrote the cached configuration; a route "
            "reading it now reports something the config tree does not say"
        )

    def test_building_really_copies(self):
        """The loop in `load_subagents`, read from the source."""
        import inspect

        from agent.src.infrastructure import subagents

        source = inspect.getsource(subagents.load_subagents)
        assert "deepcopy(declared)" in source, (
            "load_subagents must copy before inheriting, or graph setup "
            "rewrites the loader's cache"
        )
