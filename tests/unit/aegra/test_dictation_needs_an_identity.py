"""Transcribing a recording is something a person does, not anyone."""

from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from agent.aegra import speech_routes


class TestTheEndpointAsksWhoIsSpeaking:
    def test_it_takes_a_request_to_identify_the_caller(self):
        accepts = inspect.signature(speech_routes.transcribe_dictation).parameters
        assert "request" in accepts, (
            "transcribe_dictation takes no request, so it cannot know who is "
            "asking — an unauthenticated model call billed to the deployment."
        )

    def test_it_resolves_an_identity(self):
        source = inspect.getsource(speech_routes.transcribe_dictation)
        assert "authenticated_user_id" in source

    def test_it_refuses_an_anonymous_caller(self):
        source = inspect.getsource(speech_routes.transcribe_dictation)
        assert "reject_anonymous=True" in source


class TestItBehavesLikeTheSiblingUpload:
    """Attachments take the same shape and got this right."""

    def test_both_resolve_an_identity_the_same_way(self):
        from agent.aegra import attachment_routes

        theirs = inspect.getsource(attachment_routes.upload_attachments)
        mine = inspect.getsource(speech_routes.transcribe_dictation)
        assert "authenticated_user_id" in theirs
        assert "authenticated_user_id" in mine


class TestAnonymousIsRefusedInPractice:
    @pytest.mark.asyncio
    async def test_a_caller_with_no_identity_gets_nowhere(self, monkeypatch):
        """Against the function, not just its source."""
        monkeypatch.setattr(speech_routes, "_dictation_enabled", lambda: True)

        async def refuse(_request, reject_anonymous=False):
            raise HTTPException(status_code=401, detail="no identity")

        monkeypatch.setattr(speech_routes, "authenticated_user_id", refuse)

        transcribed: list[bytes] = []
        monkeypatch.setattr(
            speech_routes,
            "_to_text",
            lambda name, data: transcribed.append(data) or "heard",
        )

        with pytest.raises(HTTPException) as raised:
            await speech_routes.transcribe_dictation(
                request=object(), audio=_recording()
            )
        assert raised.value.status_code == 401
        assert transcribed == [], "the audio was transcribed for an anonymous caller"


class TestTheGateStillComesFirst:
    @pytest.mark.asyncio
    async def test_a_deployment_with_dictation_off_still_says_not_found(
        self, monkeypatch
    ):
        monkeypatch.setattr(speech_routes, "_dictation_enabled", lambda: False)

        with pytest.raises(HTTPException) as raised:
            await speech_routes.transcribe_dictation(
                request=object(), audio=_recording()
            )
        assert raised.value.status_code == 404


def _recording():
    """Enough of an upload for the route to read."""

    class Upload:
        filename = "dictation.webm"

        async def read(self) -> bytes:
            return b"audio-bytes"

    return Upload()
