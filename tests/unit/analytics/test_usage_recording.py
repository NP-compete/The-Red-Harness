"""Guards on the usage write."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.src.analytics import usage


class TestEveryParameterIsCast:
    def test_no_bare_placeholder_survives(self):
        bare = re.findall(r"%\(\w+\)s(?!::)", usage._RECORD_SQL)
        assert bare == [], f"uncast parameters in _RECORD_SQL: {bare}"

    def test_the_model_key_is_text(self):
        assert "jsonb_build_object(%(model)s::text" in usage._RECORD_SQL


class TestFailuresAreLoud:
    @pytest.mark.asyncio
    async def test_the_first_failure_warns(self, caplog):
        usage._failures = 0
        pool = MagicMock()
        pool.connection.side_effect = RuntimeError("boom")
        with patch.object(usage, "_get_pool", new=AsyncMock(return_value=pool)):
            with caplog.at_level("WARNING"):
                await usage.record_llm_usage("r1", "m", 1, 1)

        assert any("Failed to record usage" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_a_missing_run_id_is_not_a_failure(self):
        usage._failures = 0
        with patch.object(usage, "_get_pool", new=AsyncMock()) as pool:
            await usage.record_llm_usage("", "m", 1, 1)
        pool.assert_not_awaited()
        assert usage._failures == 0
