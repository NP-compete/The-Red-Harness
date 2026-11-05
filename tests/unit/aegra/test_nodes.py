"""Tests for aegra.nodes module."""

import pytest

from agent.aegra.nodes import timed_node, with_error_handling, with_retry


class TestWithErrorHandling:
    """Tests for the error-handling node decorator."""

    def test_passes_through_on_success(self):
        @with_error_handling("test-node")
        def good_node(x: int) -> int:
            return x * 2

        assert good_node(5) == 10

    def test_re_raises_on_failure(self):
        @with_error_handling("failing-node")
        def bad_node():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            bad_node()

    def test_handles_async_functions(self):
        @with_error_handling("async-node")
        async def async_node(x: int) -> int:
            return x + 1

        import asyncio

        result = asyncio.run(async_node(10))
        assert result == 11

    def test_async_error_handling(self):
        @with_error_handling("async-fail")
        async def bad_async():
            raise RuntimeError("async boom")

        import asyncio

        with pytest.raises(RuntimeError, match="async boom"):
            asyncio.run(bad_async())


class TestWithRetry:
    """Tests for the retry decorator."""

    def test_succeeds_on_first_try(self):
        call_count = 0

        @with_retry(max_retries=2, delay=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        @with_retry(max_retries=2, delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("not yet")
            return "recovered"

        assert fail_then_succeed() == "recovered"
        assert call_count == 3

    def test_exhausts_retries(self):
        attempts = 0

        @with_retry(max_retries=1, delay=0.01)
        def always_fail():
            nonlocal attempts
            attempts += 1
            raise ConnectionError("permanent failure")

        with pytest.raises(ConnectionError, match="permanent failure"):
            always_fail()
        assert attempts == 2

    def test_an_exception_it_is_not_for_is_not_retried(self):
        """A `ValueError` is a bug, not a flaky network."""
        attempts = 0

        @with_retry(max_retries=2, delay=0.01)
        def wrong():
            nonlocal attempts
            attempts += 1
            raise ValueError("a bug")

        with pytest.raises(ValueError):
            wrong()
        assert attempts == 1


class TestTimedNode:
    """Tests for the timing decorator."""

    def test_returns_result(self):
        @timed_node
        def compute(x: int) -> int:
            return x * 3

        assert compute(7) == 21

    def test_propagates_exceptions(self):
        @timed_node
        def explode():
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            explode()
