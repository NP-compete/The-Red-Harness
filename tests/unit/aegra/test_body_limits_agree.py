"""The declared limit and the streamed limit must be the same number."""

from __future__ import annotations

import pytest

from agent.aegra.security_middleware import (
    RequestSizeLimitMiddleware,
    StreamingBodyLimitMiddleware,
)

GLOBAL = 1024
OVERRIDE = {"/special": 99}

PATHS = [
    "/knowledge/documents",
    "/knowledge/sources",
    "/threads/abc/attachments",
    "/threads/abc/state",
    "/special",
    "/runs",
    "/",
]


def _declared():
    return RequestSizeLimitMiddleware(
        app=None, max_size_bytes=GLOBAL, path_limits=dict(OVERRIDE)
    )


def _streamed():
    return StreamingBodyLimitMiddleware(
        app=None, max_size_bytes=GLOBAL, path_limits=dict(OVERRIDE)
    )


@pytest.mark.parametrize("path", PATHS)
def test_both_guards_allow_the_same_number_of_bytes(path):
    assert _declared().limit_for(path) == _streamed().limit_for(path)


class TestTheUploadHeadroomIsRealOnBothSides:
    @pytest.mark.parametrize(
        "path",
        [
            "/knowledge/documents",
            "/knowledge/sources",
            "/threads/abc/attachments",
            "/threads/abc/state",
        ],
    )
    def test_an_upload_route_gets_more_than_the_global_figure(self, path):
        assert _streamed().limit_for(path) > GLOBAL

    def test_an_ordinary_route_does_not(self):
        assert _streamed().limit_for("/runs") == GLOBAL


class TestAnExplicitOverrideStillWins:
    def test_on_the_declared_side(self):
        assert _declared().limit_for("/special") == 99

    def test_on_the_streamed_side(self):
        assert _streamed().limit_for("/special") == 99

    def test_an_override_on_an_upload_route_wins_on_both(self):
        declared = RequestSizeLimitMiddleware(
            app=None, max_size_bytes=GLOBAL, path_limits={"/knowledge/documents": 7}
        )
        streamed = StreamingBodyLimitMiddleware(
            app=None, max_size_bytes=GLOBAL, path_limits={"/knowledge/documents": 7}
        )
        assert declared.limit_for("/knowledge/documents") == 7
        assert streamed.limit_for("/knowledge/documents") == 7


class TestThereIsOnePlaceThatDecides:
    def test_neither_guard_keeps_its_own_copy_of_the_rule(self):
        import inspect

        from agent.aegra import security_middleware

        source = inspect.getsource(security_middleware)
        assert source.count("_UPLOAD_SUFFIXES") <= 2
