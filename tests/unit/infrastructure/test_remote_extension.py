"""E37-T3. An extension that runs somewhere else."""

from __future__ import annotations

import pytest

from agent.src.infrastructure import remote_extension as remote
from agent.src.infrastructure.remote_extension import (
    ExtensionRefused,
    RemoteExtension,
    declared_remote,
)


class _Response:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def json(self):
        return self._body


class _Client:
    def __init__(self, answer):
        self._answer = answer
        self.asked: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def post(self, url, json):
        self.asked.append(json)
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


@pytest.fixture(autouse=True)
def _fresh_breakers(monkeypatch):
    from agent.src.security.circuit_breaker import Breakers

    monkeypatch.setattr(remote, "_breakers", Breakers(threshold=3, cooldown_seconds=60))


def _answering(monkeypatch, answer):
    client = _Client(answer)
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: client)
    return client


class TestWhatItMaySay:
    @pytest.mark.asyncio
    async def test_unchanged_leaves_the_text_alone(self, monkeypatch):
        _answering(monkeypatch, _Response({"verdict": "unchanged"}))
        extension = RemoteExtension(name="house-style", url="http://x")
        assert await extension.apply("hello") == "hello"

    @pytest.mark.asyncio
    async def test_rewritten_replaces_it(self, monkeypatch):
        _answering(monkeypatch, _Response({"verdict": "rewritten", "text": "HELLO"}))
        extension = RemoteExtension(name="house-style", url="http://x")
        assert await extension.apply("hello") == "HELLO"

    @pytest.mark.asyncio
    async def test_refused_stops_the_run_with_the_reason(self, monkeypatch):
        _answering(
            monkeypatch,
            _Response({"verdict": "refused", "reason": "contains a secret"}),
        )
        extension = RemoteExtension(name="dlp", url="http://x")
        with pytest.raises(ExtensionRefused, match="contains a secret"):
            await extension.apply("hello")

    @pytest.mark.asyncio
    async def test_it_is_told_the_tool_and_the_subject(self, monkeypatch):
        client = _answering(monkeypatch, _Response({"verdict": "unchanged"}))
        await RemoteExtension(name="x", url="http://x").apply(
            "hi", tool="execute_sql", subject="ada"
        )
        assert client.asked == [
            {
                "point": "before_model",
                "text": "hi",
                "tool": "execute_sql",
                "subject": "ada",
            }
        ]

    @pytest.mark.asyncio
    async def test_it_cannot_say_anything_else(self, monkeypatch):
        """`{"ok": true}` must not read as "this was checked"."""
        _answering(monkeypatch, _Response({"ok": True}))
        with pytest.raises(ExtensionRefused, match="did not answer with a verdict"):
            await RemoteExtension(name="dlp", url="http://x").apply("hello")


class TestWhenItDoesNotAnswer:
    @pytest.mark.asyncio
    async def test_a_required_one_refuses_the_run(self, monkeypatch):
        _answering(monkeypatch, TimeoutError("too slow"))
        with pytest.raises(ExtensionRefused, match="could not run"):
            await RemoteExtension(name="dlp", url="http://x").apply("hello")

    @pytest.mark.asyncio
    async def test_an_optional_one_returns_the_text_untouched(self, monkeypatch):
        """Untouched, not empty: an earlier draft returned '' here"""
        _answering(monkeypatch, TimeoutError("too slow"))
        extension = RemoteExtension(name="style", url="http://x", required=False)
        assert await extension.apply("hello") == "hello"

    @pytest.mark.asyncio
    async def test_an_error_status_is_a_failure_not_a_pass(self, monkeypatch):
        _answering(monkeypatch, _Response({"verdict": "unchanged"}, status=503))
        with pytest.raises(ExtensionRefused, match="503"):
            await RemoteExtension(name="dlp", url="http://x").apply("hello")

    @pytest.mark.asyncio
    async def test_rewritten_with_no_text_is_not_a_rewrite(self, monkeypatch):
        """Treated as unreadable rather than as an empty rewrite,"""
        _answering(monkeypatch, _Response({"verdict": "rewritten"}))
        with pytest.raises(ExtensionRefused, match="did not answer with a verdict"):
            await RemoteExtension(name="dlp", url="http://x").apply("hello")

    @pytest.mark.asyncio
    async def test_a_refusal_is_carried_even_when_outages_are_tolerated(
        self, monkeypatch
    ):
        """Fail-open is about the extension being *down*, not about"""
        _answering(monkeypatch, _Response({"verdict": "refused", "reason": "no"}))
        extension = RemoteExtension(name="dlp", url="http://x", required=False)
        with pytest.raises(ExtensionRefused):
            await extension.apply("hello")


class TestTheBreaker:
    @pytest.mark.asyncio
    async def test_it_stops_asking_after_repeated_failures(self, monkeypatch):
        client = _answering(monkeypatch, TimeoutError("down"))
        extension = RemoteExtension(name="style", url="http://x", required=False)
        for _ in range(4):
            await extension.apply("hello")
        assert len(client.asked) == 0 or extension.unavailable()


class TestReadingTheDeclaration:
    def test_a_url_is_required(self):
        with pytest.raises(ValueError, match="needs a url"):
            declared_remote({})

    def test_it_must_be_http(self):
        with pytest.raises(ValueError, match="not an http"):
            declared_remote({"url": "file:///etc/passwd"})

    def test_the_default_is_to_refuse_without_it(self):
        assert declared_remote({"url": "http://x"}).required is True

    def test_an_unknown_failure_mode_is_refused(self):
        with pytest.raises(ValueError, match="not a usable on_failure"):
            declared_remote({"url": "http://x", "on_failure": "maybe"})

    def test_a_zero_timeout_is_refused(self):
        with pytest.raises(ValueError, match="never lets anything answer"):
            declared_remote({"url": "http://x", "timeout_seconds": 0})


class TestTheFourPoints:
    """E37-T1. Four points, each the same question with a different"""

    def test_the_default_is_before_the_model_only(self):
        assert declared_remote({"url": "http://x"}).points == ("before_model",)

    def test_a_deployment_may_ask_for_all_four(self):
        asked = declared_remote(
            {
                "url": "http://x",
                "points": ["before_model", "after_model", "before_tool", "after_tool"],
            }
        )
        assert len(asked.points) == 4
        assert asked.asked_at("after_tool")

    def test_a_point_nobody_has_is_refused_by_name(self):
        """A typo'd point silently dropped is an extension a"""
        with pytest.raises(ValueError, match="'befor_model' is not an extension point"):
            declared_remote({"url": "http://x", "points": ["befor_model"]})

    def test_a_bare_string_is_refused(self):
        with pytest.raises(ValueError, match="is a list of"):
            declared_remote({"url": "http://x", "points": "before_model"})

    @pytest.mark.asyncio
    async def test_the_point_travels_with_the_payload(self, monkeypatch):
        client = _answering(monkeypatch, _Response({"verdict": "unchanged"}))
        extension = RemoteExtension(name="x", url="http://x")
        await extension.apply("hi", point="after_tool", tool="execute_sql")
        assert client.asked[0]["point"] == "after_tool"

    def test_an_extension_is_only_asked_where_it_said(self):
        extension = declared_remote({"url": "http://x", "points": ["after_tool"]})
        assert extension.asked_at("after_tool")
        assert not extension.asked_at("before_model")
