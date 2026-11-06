"""OpenAPI drift against a committed baseline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from tests.fixtures.openapi import diff_schemas, operations

BASELINE = Path(__file__).parents[2] / "fixtures" / "openapi-baseline.json"


@pytest.fixture(scope="module")
def baseline() -> dict:
    assert BASELINE.is_file(), (
        f"No OpenAPI baseline at {BASELINE} — generate with: make openapi-baseline"
    )
    return json.loads(BASELINE.read_text())


@pytest.fixture(scope="module")
def current() -> dict:
    """Build the app the way `make openapi-baseline` does."""
    with tempfile.NamedTemporaryFile("r", suffix=".json") as handle:
        code = (
            "import json,sys;"
            "from aegra_api.main import create_app;"
            "open(sys.argv[1],'w').write(json.dumps(create_app().openapi()))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code, handle.name],
            capture_output=True,
            text=True,
            env={**os.environ, "UI_CONFIG_MODE": "readwrite"},
            cwd=Path(__file__).parents[2].parent,
        )
        assert out.returncode == 0, out.stderr[-2000:]
        return json.loads(Path(handle.name).read_text())


class TestOpenApiDrift:
    def test_no_breaking_changes(self, baseline: dict, current: dict):
        diff = diff_schemas(baseline, current)

        assert not diff.is_breaking, (
            "Breaking OpenAPI change:\n  "
            + "\n  ".join(diff.breaking)
            + "\n\nIf intended, regenerate with: make openapi-baseline"
        )

    def test_additive_changes_are_reported_not_failed(
        self, baseline: dict, current: dict, capsys
    ):
        """Adding a route cannot break a client, so it must not fail CI."""
        diff = diff_schemas(baseline, current)

        if diff.added_operations:
            print("New operations since baseline:", diff.added_operations)

    def test_baseline_covers_a_realistic_surface(self, baseline: dict):
        """Guards against a baseline regenerated from a half-built app."""
        assert len(operations(baseline)) > 50


class TestDifferSemantics:
    """The differ must not pass everything — that is the failure mode"""

    def test_removed_operation_is_breaking(self):
        before = {"paths": {"/a": {"get": {}}, "/b": {"post": {}}}}
        after = {"paths": {"/a": {"get": {}}}}

        assert diff_schemas(before, after).is_breaking

    def test_removed_method_on_a_kept_path_is_breaking(self):
        before = {"paths": {"/a": {"get": {}, "delete": {}}}}
        after = {"paths": {"/a": {"get": {}}}}

        assert diff_schemas(before, after).is_breaking

    def test_added_operation_is_not_breaking(self):
        before = {"paths": {"/a": {"get": {}}}}
        after = {"paths": {"/a": {"get": {}}, "/b": {"get": {}}}}

        diff = diff_schemas(before, after)
        assert not diff.is_breaking
        assert diff.added_operations == ["GET /b"]

    def test_newly_required_field_is_breaking(self):
        """A caller that already omits the field starts failing."""
        before = {"components": {"schemas": {"S": {"required": ["a"]}}}}
        after = {"components": {"schemas": {"S": {"required": ["a", "b"]}}}}

        assert diff_schemas(before, after).is_breaking

    def test_relaxing_a_requirement_is_not_breaking(self):
        before = {"components": {"schemas": {"S": {"required": ["a", "b"]}}}}
        after = {"components": {"schemas": {"S": {"required": ["a"]}}}}

        assert not diff_schemas(before, after).is_breaking

    def test_removed_schema_is_breaking(self):
        before = {"components": {"schemas": {"S": {"required": []}}}}
        after = {"components": {"schemas": {}}}

        assert diff_schemas(before, after).is_breaking

    def test_identical_schemas_are_clean(self):
        schema = {
            "paths": {"/a": {"get": {}}},
            "components": {"schemas": {"S": {"required": ["x"]}}},
        }

        diff = diff_schemas(schema, schema)
        assert not diff.is_breaking
        assert diff.added_operations == []
