"""Tests for run admission control."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agent.aegra.admission import AdmissionControlMiddleware


def _app(max_concurrent: int, hold: asyncio.Event | None = None) -> FastAPI:
    app = FastAPI()

    @app.post("/threads/{thread_id}/runs")
    async def start_run(thread_id: str):
        if hold is not None:
            await hold.wait()
        return {"ok": thread_id}

    @app.post("/runs")
    async def start_bare_run():
        if hold is not None:
            await hold.wait()
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/threads/{thread_id}/runs")
    async def list_runs(thread_id: str):
        return {"runs": []}

    app.add_middleware(AdmissionControlMiddleware, max_concurrent=max_concurrent)
    return app


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestAdmissionControl:
    async def test_admits_below_the_limit(self):
        async with await _client(_app(2)) as c:
            r = await c.post("/threads/t1/runs")
        assert r.status_code == 200

    async def test_sheds_at_the_limit(self):
        """A full pod says so immediately rather than queueing."""
        hold = asyncio.Event()
        app = _app(1, hold)
        async with await _client(app) as c:
            first = asyncio.create_task(c.post("/runs"))
            await asyncio.sleep(0)
            second = await c.post("/runs")

            assert second.status_code == 503
            assert second.json()["error_type"] == "at_capacity"
            assert second.headers["Retry-After"] == "5"

            hold.set()
            assert (await first).status_code == 200

    async def test_capacity_is_returned_after_a_run_finishes(self):
        hold = asyncio.Event()
        app = _app(1, hold)
        async with await _client(app) as c:
            first = asyncio.create_task(c.post("/runs"))
            await asyncio.sleep(0)
            hold.set()
            await first

            second = await c.post("/runs")
        assert second.status_code == 200

    @pytest.mark.parametrize("path", ["/health", "/threads/t1/runs"])
    async def test_reads_are_never_gated(self, path):
        """A pod at capacity still answers probes and polling."""
        hold = asyncio.Event()
        app = _app(1, hold)
        async with await _client(app) as c:
            running = asyncio.create_task(c.post("/runs"))
            await asyncio.sleep(0)

            assert (await c.get(path)).status_code == 200

            hold.set()
            await running

    async def test_zero_disables_the_gate(self):
        hold = asyncio.Event()
        app = _app(0, hold)
        async with await _client(app) as c:
            tasks = [asyncio.create_task(c.post("/runs")) for _ in range(5)]
            await asyncio.sleep(0)
            hold.set()
            results = await asyncio.gather(*tasks)
        assert [r.status_code for r in results] == [200] * 5


class TestThePermitSpansTheWholeResponse:
    """`call_next` returns when the response starts, not when it ends."""

    @staticmethod
    def _middleware(max_concurrent: int = 1):
        from agent.aegra.admission import AdmissionControlMiddleware

        return AdmissionControlMiddleware(app=None, max_concurrent=max_concurrent)

    @staticmethod
    def _streaming_request():
        from unittest.mock import MagicMock

        request = MagicMock()
        request.method = "POST"
        request.url.path = "/threads/abc/runs/stream"
        return request

    async def test_the_permit_is_still_held_while_the_body_streams(self):
        mw = self._middleware()

        async def body():
            yield b"chunk-1"
            yield b"chunk-2"

        from unittest.mock import MagicMock

        response = MagicMock()
        response.body_iterator = body()

        async def call_next(_request):
            return response

        out = await mw.dispatch(self._streaming_request(), call_next)
        assert mw._sem.locked()

        chunks = [c async for c in out.body_iterator]
        assert chunks == [b"chunk-1", b"chunk-2"]
        assert not mw._sem.locked()

    async def test_a_plain_response_releases_immediately(self):
        from unittest.mock import MagicMock

        mw = self._middleware()
        response = MagicMock()
        del response.body_iterator

        async def call_next(_request):
            return response

        await mw.dispatch(self._streaming_request(), call_next)
        assert not mw._sem.locked()

    async def test_a_failure_does_not_strand_the_permit(self):
        mw = self._middleware()

        async def call_next(_request):
            raise RuntimeError("upstream died")

        import pytest

        with pytest.raises(RuntimeError):
            await mw.dispatch(self._streaming_request(), call_next)
        assert not mw._sem.locked()

    async def test_a_client_that_disconnects_mid_stream_releases(self):
        mw = self._middleware()

        async def body():
            yield b"chunk-1"
            raise ConnectionResetError("client went away")

        from unittest.mock import MagicMock

        response = MagicMock()
        response.body_iterator = body()

        async def call_next(_request):
            return response

        out = await mw.dispatch(self._streaming_request(), call_next)
        import pytest

        with pytest.raises(ConnectionResetError):
            async for _ in out.body_iterator:
                pass
        assert not mw._sem.locked()


class TestAPodOnTheWayOut:
    """A run this pod will not finish is worse than one it never began."""

    @pytest.fixture
    def draining(self, monkeypatch):
        monkeypatch.setattr("agent.aegra.shutdown.is_shutting_down", lambda: True)

    async def test_a_new_run_is_refused_while_shutting_down(self, draining):
        async with await _client(_app(4)) as c:
            answer = await c.post("/threads/t1/runs")
        assert answer.status_code == 503
        assert answer.json()["error_type"] == "shutting_down"

    async def test_it_does_not_tell_the_caller_to_come_back_here(self, draining):
        """No Retry-After: this pod is going away, and five seconds"""
        async with await _client(_app(4)) as c:
            answer = await c.post("/threads/t1/runs")
        assert "retry-after" not in {k.lower() for k in answer.headers}

    async def test_reads_still_answer_while_shutting_down(self, draining):
        """A draining pod still has to answer a poll about a run"""
        async with await _client(_app(4)) as c:
            answer = await c.get("/threads/t1/runs")
        assert answer.status_code == 200

    async def test_the_gate_applies_even_with_the_limit_off(self, draining):
        """`max_concurrent=0` turns off the capacity bound, not the"""
        async with await _client(_app(0)) as c:
            answer = await c.post("/threads/t1/runs")
        assert answer.status_code == 503
        assert answer.json()["error_type"] == "shutting_down"
