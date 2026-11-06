"""Usage split by assistant."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from agent.src.analytics import queries


class TestTheQueryItself:
    def test_there_is_one(self):
        assert hasattr(queries, "by_assistant")

    def test_the_window_is_a_bound_parameter(self):
        import inspect

        source = inspect.getsource(queries.by_assistant)
        assert "%(days)s" in source
        assert "make_interval" in source

    def test_only_known_constants_are_interpolated(self):
        import inspect
        import re

        source = inspect.getsource(queries.by_assistant)
        sql = source[source.index('"""', source.index("sql")) :].split('"""')[1]
        allowed = {"_CLIENT_ONLY", "_CLIENT_ONLY_R", "_TERMINAL"}
        assert set(re.findall(r"\{(\w+)\}", sql)) <= allowed

    def test_the_caller_supplied_window_is_not_among_them(self):
        import inspect
        import re

        source = inspect.getsource(queries.by_assistant)
        sql = source[source.index('"""', source.index("sql")) :].split('"""')[1]
        assert "days" not in set(re.findall(r"\{(\w+)\}", sql))

    def test_it_groups_by_assistant(self):
        import inspect

        assert "assistant_id" in inspect.getsource(queries.by_assistant)

    def test_it_only_counts_runs_in_the_window(self):
        import inspect

        source = inspect.getsource(queries.by_assistant)
        assert "created_at >=" in source

    def test_it_counts_client_traffic_only(self):
        import inspect

        assert "_CLIENT_ONLY_R" in inspect.getsource(queries.by_assistant)


class TestTheRoute:
    @pytest.mark.asyncio
    async def test_it_returns_the_rows(self):
        from agent.aegra import analytics_routes as ar

        rows = [{"assistant": "agent", "runs": 3}]
        with patch.object(queries, "by_assistant", new=AsyncMock(return_value=rows)):
            body = await ar.analytics_assistants(days=7, _token="t")
        assert body["assistants"] == rows

    @pytest.mark.asyncio
    async def test_a_failure_is_not_an_empty_breakdown(self):
        from agent.aegra import analytics_routes as ar

        with (
            patch.object(
                queries, "by_assistant", new=AsyncMock(side_effect=RuntimeError("down"))
            ),
            pytest.raises(HTTPException) as refused,
        ):
            await ar.analytics_assistants(days=7, _token="t")
        assert refused.value.status_code == 503


class TestItCanBeExported:
    def test_the_report_is_offered(self):
        assert "assistants" in queries.EXPORTABLE

    def test_it_points_at_the_query(self):
        assert queries.EXPORTABLE["assistants"] == "by_assistant"

    def test_every_exportable_report_names_a_real_query(self):
        for what, name in queries.EXPORTABLE.items():
            assert callable(getattr(queries, name, None)), f"{what} names no query"
