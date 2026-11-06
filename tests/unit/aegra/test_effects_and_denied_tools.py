"""A denied tool is taken away, not merely gated."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent.src.agent.config.hitl import denied_tool_names
from agent.src.agent.config.middleware import HumanApprovalConfig


def _tool(name: str):
    t = MagicMock()
    t.name = name
    return t


class TestDryRunDeniesActingTools:
    """`dry_run` turns "ask a human" into "refuse"."""

    CONFIG = HumanApprovalConfig(enabled=True, mode="all", exclude=[])

    def test_live_asks_rather_than_denies(self):
        denied = denied_tool_names(self.CONFIG, [_tool("write_file")], effects="live")
        assert "write_file" not in denied

    def test_dry_run_denies_the_same_tool(self):
        denied = denied_tool_names(
            self.CONFIG, [_tool("write_file")], effects="dry_run"
        )
        assert "write_file" in denied

    def test_an_excluded_tool_survives_dry_run(self):
        """Investigating is the point of a dry run."""
        config = HumanApprovalConfig(enabled=True, mode="all", exclude=["read_file"])
        denied = denied_tool_names(config, [_tool("read_file")], effects="dry_run")
        assert "read_file" not in denied


class TestEffectsModeIsReadFromTheTopLevel:
    """`execution:` sits at the top level of agent.yaml."""

    def test_loader_reads_the_top_level_key(self):
        from agent.src.agent.config.loader import AgentConfig
        from agent.src.agent.config.middleware import ExecutionConfig

        loader = object.__new__(AgentConfig)
        loader._execution_config = ExecutionConfig(effects="dry_run")
        loader._ensure_loaded = lambda: None  # type: ignore[method-assign]
        assert loader.get_effects_mode() == "dry_run"

    def test_the_admin_endpoint_reports_what_the_loader_says(self):
        from agent.aegra import admin_routes

        with patch(
            "agent.src.agent.config.agent_config.get_effects_mode",
            return_value="dry_run",
        ):
            assert admin_routes._effects_mode() == "dry_run"


class TestGraphCacheIsPerUser:
    """The compiled graph carries one person's integration state."""

    @staticmethod
    def _key(user: str):
        from agent.aegra.graph import _graph_fingerprint

        return _graph_fingerprint(
            "gemini-3.8-flash",
            "prompt",
            ["read_file"],
            user_identity=user,
        )

    def test_two_users_do_not_share_a_graph(self):
        assert self._key("alice") != self._key("bob")

    def test_the_same_user_still_hits_the_cache(self):
        assert self._key("alice") == self._key("alice")

    def test_an_anonymous_run_is_its_own_bucket(self):
        assert self._key("") != self._key("alice")


class TestDenialReachesEverything:
    """Removing a denied tool from the orchestrator is not enough."""

    @staticmethod
    def _excluded():
        from agent.src.infrastructure.middleware import _profile_excluded_tools

        return _profile_excluded_tools()

    def test_denied_names_join_the_shared_exclusion_list(self):
        from agent.src.infrastructure.middleware import set_policy_denied_tools

        set_policy_denied_tools(["write_file", "dataverse_execute_sql"])
        try:
            excluded = self._excluded()
        finally:
            set_policy_denied_tools([])
        assert "write_file" in excluded
        assert "dataverse_execute_sql" in excluded

    def test_nothing_denied_adds_nothing(self):
        from agent.src.infrastructure.middleware import set_policy_denied_tools

        set_policy_denied_tools([])
        before = self._excluded()
        assert "write_file" not in before

    def test_subagents_read_the_same_list(self):
        """One source, so the two cannot disagree."""
        import inspect

        from agent.src.infrastructure import subagents

        source = inspect.getsource(subagents)
        assert "_build_tool_exclusions(_profile_excluded_tools(" in source
