"""Where a `filesystem_readonly` route reads from."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import agent.src.infrastructure.backend as backend


@pytest.fixture
def base(tmp_path: Path):
    with patch.object(backend, "agent_config") as cfg:
        cfg.base_dir = tmp_path
        yield tmp_path


class TestReadonlyRoot:
    def test_bare_name_resolves_under_the_config_dir(self, base):
        assert (
            backend._readonly_root("/skills/", "filesystem_readonly") == base / "skills"
        )

    def test_an_absolute_path_is_used_as_given(self, base):
        assert backend._readonly_root(
            "/datasets/", "filesystem_readonly:/app/data/datasets"
        ) == Path("/app/data/datasets")

    def test_documents_resolve_where_uploads_are_written(self, base):
        """The one route a person writes to through the interface."""
        from agent.src.data_paths import documents_dir

        assert (
            backend._readonly_root(
                "/documents/", "filesystem_readonly:/app/data/documents"
            )
            == documents_dir()
        )

    def test_a_relative_path_stays_under_the_config_dir(self, base):
        assert (
            backend._readonly_root("/x/", "filesystem_readonly:extra") == base / "extra"
        )

    def test_the_route_prefix_is_not_the_path(self, base):
        assert backend._readonly_root(
            "/datasets/", "filesystem_readonly:/mnt/corpus"
        ) == Path("/mnt/corpus")
