"""Every NFR-DEP constraint has a test that checks it (TEST-4)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

HERE = Path(__file__).parent

COVERED: dict[str, tuple[str, ...]] = {
    "DEP-1": (
        "test_no_container_is_privileged",
        "test_no_privilege_escalation",
        "test_no_hardcoded_runasuser",
        "test_no_host_namespaces_or_host_path",
        "test_the_data_directory_is_group_writable",
        "test_the_container_does_not_run_as_root",
    ),
    "DEP-2": ("test_every_container_declares_resources",),
    "DEP-3": ("test_ingress_is_a_route_in_openshift", "test_nginx_is_kind_only"),
    "DEP-4": (
        "test_every_other_claim_is_read_write_once",
        "test_the_documents_claim_really_is_the_wider_one",
        "test_the_chart_ships_read_write_many_for_documents",
        "test_it_is_not_derived_from_the_target_alone",
        "test_it_carries_the_process_and_a_nonce",
        "test_two_writers_get_two_names",
    ),
    "DEP-5": (
        "test_no_mount_points_at_a_volume_that_is_gone",
        "test_the_render_keeps_every_source_volume",
    ),
    "DEP-6": ("test_the_config_volume_is_mounted_read_only",),
    "DEP-7": (
        "test_routes_raise_the_haproxy_idle_timeout",
        "test_the_external_route_does_not_inherit_the_streaming_timeout",
    ),
}

UNTESTED: dict[str, str] = {}


def _test_names() -> set[str]:
    """Every test function defined in this directory."""
    found: set[str] = set()
    for path in sorted(HERE.glob("test_*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test"):
                    found.add(node.name)
    return found


class TestTheMapIsHonest:
    @pytest.mark.parametrize("requirement", sorted(COVERED))
    def test_every_named_test_exists(self, requirement):
        missing = [one for one in COVERED[requirement] if one not in _test_names()]
        assert not missing, (
            f"{requirement} claims {missing}, which do not exist. A map to a "
            "test that is gone is worse than no map: it reads as covered."
        )

    def test_no_constraint_is_in_both_lists(self):
        assert not (set(COVERED) & set(UNTESTED))

    def test_every_constraint_is_accounted_for(self):
        every = {f"DEP-{n}" for n in range(1, 8)}
        assert set(COVERED) | set(UNTESTED) == every, sorted(
            every - (set(COVERED) | set(UNTESTED))
        )

    @pytest.mark.parametrize("requirement", sorted(UNTESTED))
    def test_an_excuse_says_something(self, requirement):
        assert len(UNTESTED[requirement]) > 60


class TestTheGapsAreNotGrowing:
    def test_nothing_is_untested(self):
        """A ratchet on the shape of the map, not its contents."""
        assert len(UNTESTED) == 0, sorted(UNTESTED)
