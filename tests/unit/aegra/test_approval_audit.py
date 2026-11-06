"""Approval decisions reach the audit trail (CLI-6, E28-T5)."""

from __future__ import annotations

import json

import pytest

from agent.aegra.approval_audit import (
    ApprovalAuditMiddleware,
    decisions_in,
    summarise,
)

RESUME = json.dumps(
    {
        "assistant_id": "agent",
        "command": {"resume": {"decisions": [{"type": "approve"}]}},
    }
).encode()

MESSAGE = json.dumps({"assistant_id": "agent", "input": {"messages": []}}).encode()


class TestWhatCountsAsADecision:
    def test_a_resume_is_one(self):
        assert decisions_in(RESUME) == [{"type": "approve"}]

    def test_a_new_message_is_not(self):
        assert decisions_in(MESSAGE) is None

    def test_an_unfamiliar_resume_shape_still_counts(self):
        body = json.dumps({"command": {"resume": "approve"}}).encode()
        assert decisions_in(body) == []

    def test_nonsense_is_not_a_decision(self):
        assert decisions_in(b"not json") is None
        assert decisions_in(b"") is None

    def test_an_enormous_body_is_not_inspected(self):
        assert decisions_in(b"{" + b"x" * (300 * 1024)) is None


class TestWhatIsRecorded:
    def test_the_decision_types(self):
        found = summarise([{"type": "approve"}, {"type": "reject"}])
        assert found["decisions"] == ["approve", "reject"]
        assert found["count"] == 2

    def test_whether_a_rejection_was_explained_but_not_what_it_said(self):
        found = summarise([{"type": "reject", "message": "we do not email customers"}])
        assert found["explained"] is True
        assert "customers" not in json.dumps(found)


class TestTheBodySurvives:
    async def _run(self, body: bytes, path="/threads/t-1/runs/wait", method="POST"):
        seen: dict = {}

        async def app(scope, receive, send):
            chunks = []
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    break
                chunks.append(message.get("body") or b"")
                if not message.get("more_body"):
                    break
            seen["body"] = b"".join(chunks)

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        await ApprovalAuditMiddleware(app)(
            {"type": "http", "method": method, "path": path, "headers": []},
            receive,
            lambda _m: None,
        )
        return seen

    @pytest.mark.asyncio
    async def test_the_application_still_gets_it(self):
        assert (await self._run(RESUME))["body"] == RESUME

    @pytest.mark.asyncio
    async def test_a_body_in_pieces_arrives_whole(self):
        seen: dict = {}
        pieces = [b'{"command": {"resume"', b': {"decisions": []}}}']

        async def app(scope, receive, send):
            chunks = []
            while True:
                message = await receive()
                chunks.append(message.get("body") or b"")
                if not message.get("more_body"):
                    break
            seen["body"] = b"".join(chunks)

        sent = iter(
            [
                {"type": "http.request", "body": pieces[0], "more_body": True},
                {"type": "http.request", "body": pieces[1], "more_body": False},
            ]
        )

        async def receive():
            return next(sent)

        await ApprovalAuditMiddleware(app)(
            {
                "type": "http",
                "method": "POST",
                "path": "/threads/t/runs",
                "headers": [],
            },
            receive,
            lambda _m: None,
        )
        assert seen["body"] == b"".join(pieces)

    @pytest.mark.asyncio
    async def test_everything_after_the_body_comes_from_the_real_receive(self):
        asked: list[str] = []

        async def app(scope, receive, send):
            await receive()
            after = await receive()
            asked.append(after["type"])

        async def receive():
            if not asked:
                return {"type": "http.request", "body": RESUME, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        await ApprovalAuditMiddleware(app)(
            {
                "type": "http",
                "method": "POST",
                "path": "/threads/t/runs/wait",
                "headers": [],
            },
            receive,
            lambda _m: None,
        )
        assert asked == ["http.request"]

    @pytest.mark.asyncio
    async def test_another_route_is_passed_straight_through(self):
        assert (await self._run(MESSAGE, path="/config/tree"))["body"] == MESSAGE

    @pytest.mark.asyncio
    async def test_so_is_a_get(self):
        assert (await self._run(b"", method="GET"))["body"] == b""


class TestABodyTooBigToBotherWith:
    """Past the inspection cap, it stops holding the rest."""

    @pytest.mark.asyncio
    async def test_the_whole_body_still_reaches_the_application(self):
        from agent.aegra.approval_audit import MAX_BODY

        pieces = [b"x" * (MAX_BODY + 1), b"y" * 32, b"z" * 8]
        seen: dict = {}

        async def app(scope, receive, send):
            chunks = []
            while True:
                message = await receive()
                chunks.append(message.get("body") or b"")
                if not message.get("more_body"):
                    break
            seen["body"] = b"".join(chunks)

        sent = iter(
            [
                {
                    "type": "http.request",
                    "body": one,
                    "more_body": index < len(pieces) - 1,
                }
                for index, one in enumerate(pieces)
            ]
        )

        async def receive():
            return next(sent)

        await ApprovalAuditMiddleware(app)(
            {
                "type": "http",
                "method": "POST",
                "path": "/threads/t/runs",
                "headers": [],
            },
            receive,
            lambda _m: None,
        )
        assert seen["body"] == b"".join(pieces)

    @pytest.mark.asyncio
    async def test_nothing_is_recorded_for_one(self, monkeypatch):
        import agent.aegra.approval_audit as module

        async def refuse(*_args, **_rest):
            raise AssertionError("recorded a body it never read")

        monkeypatch.setattr(module, "record", refuse)

        async def app(scope, receive, send):
            while (await receive()).get("more_body"):
                pass

        sent = iter(
            [
                {
                    "type": "http.request",
                    "body": b"x" * (module.MAX_BODY + 1),
                    "more_body": True,
                },
                {"type": "http.request", "body": b"y", "more_body": False},
            ]
        )

        async def receive():
            return next(sent)

        await ApprovalAuditMiddleware(app)(
            {
                "type": "http",
                "method": "POST",
                "path": "/threads/t/runs",
                "headers": [],
            },
            receive,
            lambda _m: None,
        )
