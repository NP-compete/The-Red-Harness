"""A configuration tree for measuring, separate from the one that works."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
BENCH = REPO / "config" / "bench"
SHIPPED = REPO / "config" / "agent"


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


class TestThereIsOne:
    def test_the_tree_exists(self):
        assert BENCH.is_dir()

    def test_it_has_the_files_an_agent_cannot_start_without(self):
        for required in ("PROMPT.md", "runtime/agent.yaml"):
            assert (BENCH / required).is_file(), required

    def test_it_declares_a_schema_version(self):
        from agent.src.agent.config.schema_version import CURRENT

        assert _yaml(BENCH / "runtime" / "agent.yaml")["schema_version"] == CURRENT

    def test_it_loads_against_the_current_models(self):
        from scripts.config.validate_configs import check_trees

        failed = [r.name for r in check_trees(BENCH) if not r.ok]
        assert failed == []


class TestItIsNotTheShippedTree:
    def test_the_agent_is_named_differently(self):
        assert (
            _yaml(BENCH / "runtime" / "agent.yaml")["name"]
            != _yaml(SHIPPED / "runtime" / "agent.yaml")["name"]
        )

    def test_its_prompt_is_its_own(self):
        assert (BENCH / "PROMPT.md").read_text() != (SHIPPED / "PROMPT.md").read_text()

    def test_it_reaches_no_remote_servers(self):
        from agent.src.agent.config.loader import _load_jsonc

        found = _load_jsonc(BENCH / "integrations" / "mcp.json")
        assert found.get("mcpServers", {}) == {}

    def test_it_cannot_change_anything(self):
        found = _yaml(BENCH / "runtime" / "agent.yaml")
        assert (found.get("execution") or {}).get("effects") == "dry_run"


class TestTheShippedTreeIsUntouched:
    """The property that actually matters."""

    def test_the_shipped_tree_is_still_the_shipped_tree(self):
        assert _yaml(SHIPPED / "runtime" / "agent.yaml")["name"] == "Workpilot"

    def test_the_shipped_tree_still_has_its_servers(self):
        from agent.src.agent.config.loader import _load_jsonc

        found = _load_jsonc(SHIPPED / "integrations" / "mcp.json")
        assert found.get("mcpServers")

    def test_nothing_in_the_bench_tree_points_at_the_shipped_one(self):
        for path in BENCH.rglob("*"):
            if path.is_file():
                assert "config/agent" not in path.read_text(errors="replace"), path


class TestWhatABenchRunIsAllowedToDo:
    @staticmethod
    def _bench() -> dict:
        return (_yaml(BENCH / "runtime" / "agent.yaml").get("bench")) or {}

    def test_it_is_off(self):
        assert self._bench()["enabled"] is False

    def test_it_names_the_suites(self):
        assert self._bench()["suites"]

    def test_the_model_is_empty_so_the_agents_own_is_used(self):
        assert self._bench()["model"] == ""

    def test_it_has_a_wall(self):
        assert self._bench()["timeout_seconds"] > 0

    @pytest.mark.parametrize("field", ["parallel", "results_path"])
    def test_the_rest_is_declared(self, field):
        assert field in self._bench()


class TestTheModelThatReadsIt:
    def test_a_tree_with_no_bench_block_is_off(self):
        from scripts.bench.profile import read_bench

        assert read_bench({}).enabled is False

    def test_the_block_is_read(self):
        from scripts.bench.profile import read_bench

        found = read_bench({"bench": {"enabled": True, "parallel": 8}})
        assert found.parallel == 8

    def test_suites_come_back_as_a_list(self):
        from scripts.bench.profile import read_bench

        assert read_bench({"bench": {"suites": ["jb", "lab"]}}).suites == ("jb", "lab")

    def test_a_parallelism_of_nothing_is_refused(self):
        from scripts.bench.profile import BenchMisconfigured, read_bench

        with pytest.raises(BenchMisconfigured):
            read_bench({"bench": {"parallel": 0}})

    def test_a_wall_of_no_time_is_refused(self):
        from scripts.bench.profile import BenchMisconfigured, read_bench

        with pytest.raises(BenchMisconfigured):
            read_bench({"bench": {"timeout_seconds": 0}})

    def test_the_refusal_names_the_setting(self):
        from scripts.bench.profile import BenchMisconfigured, read_bench

        with pytest.raises(BenchMisconfigured, match="timeout_seconds"):
            read_bench({"bench": {"timeout_seconds": -1}})
