"""Dictating into the composer."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from agent.aegra import speech_routes


class _Upload:
    """Stands in for an uploaded recording."""

    def __init__(
        self, data: bytes = b"audio", filename: str = "dictation.webm"
    ) -> None:
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data


@pytest.fixture(autouse=True)
def _signed_in(monkeypatch):
    """Somebody is signed in, for every test here."""

    async def who(_request, reject_anonymous=False):
        return "ada"

    monkeypatch.setattr(speech_routes, "authenticated_user_id", who)


@pytest.fixture
def allowed(monkeypatch):
    def set(enabled: bool = True):
        monkeypatch.setattr(speech_routes, "_dictation_enabled", lambda: enabled)

    return set


@pytest.mark.asyncio
async def test_nothing_is_transcribed_unless_the_deployment_turned_it_on(allowed):
    """A deployment that enables nothing sends no audio anywhere."""
    allowed(False)
    with pytest.raises(HTTPException) as exc:
        await speech_routes.transcribe_dictation(request=object(), audio=_Upload())  # type: ignore[arg-type]
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_dictation_is_off_until_it_is_switched_on():
    from agent.src.settings import settings

    assert settings.DICTATION_ENABLED is False


@pytest.mark.asyncio
async def test_says_dictation_is_unavailable_when_it_is(allowed):
    allowed(False)
    assert (await speech_routes.speech_capabilities())["dictation"] is False


@pytest.mark.asyncio
async def test_says_dictation_is_available_when_it_is(allowed):
    allowed(True)
    assert (await speech_routes.speech_capabilities())["dictation"] is True


@pytest.mark.asyncio
async def test_hands_back_what_was_said(allowed):
    allowed(True)
    with patch.object(speech_routes, "_to_text", return_value="  book the room  "):
        found = await speech_routes.transcribe_dictation(
            request=object(), audio=_Upload()
        )  # type: ignore[arg-type]
    assert found["text"] == "book the room"


@pytest.mark.asyncio
async def test_an_empty_recording_is_refused_rather_than_sent(allowed):
    allowed(True)
    with pytest.raises(HTTPException) as exc:
        await speech_routes.transcribe_dictation(
            request=object(), audio=_Upload(data=b"")
        )  # type: ignore[arg-type]
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_a_recording_too_large_to_send_says_so(allowed):
    allowed(True)
    big = _Upload(data=b"x" * (speech_routes.MAX_DICTATION_BYTES + 1))
    with pytest.raises(HTTPException) as exc:
        await speech_routes.transcribe_dictation(request=object(), audio=big)  # type: ignore[arg-type]
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_a_recording_that_is_not_audio_is_refused(allowed):
    allowed(True)
    with pytest.raises(HTTPException) as exc:
        await speech_routes.transcribe_dictation(
            request=object(), audio=_Upload(filename="notes.txt")
        )  # type: ignore[arg-type]
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_an_engine_that_cannot_transcribe_says_why(allowed):
    from agent.src.knowledge.transcribe import TranscriptionUnavailable

    allowed(True)
    with patch.object(
        speech_routes, "_to_text", side_effect=TranscriptionUnavailable("too long")
    ):
        with pytest.raises(HTTPException) as exc:
            await speech_routes.transcribe_dictation(request=object(), audio=_Upload())  # type: ignore[arg-type]
    assert exc.value.status_code == 422 and "too long" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_silence_comes_back_as_nothing_rather_than_as_a_failure(allowed):
    allowed(True)
    with patch.object(speech_routes, "_to_text", return_value="   "):
        found = await speech_routes.transcribe_dictation(
            request=object(), audio=_Upload()
        )  # type: ignore[arg-type]
    assert found["text"] == ""


@pytest.mark.asyncio
async def test_a_deployment_can_name_the_engine_that_hears_its_audio(monkeypatch):
    """An in-region engine is a setting, not a code change."""
    from agent.src.settings import settings

    monkeypatch.setattr(settings, "DICTATION_MODEL", "in-region-speech")
    assert speech_routes._dictation_model() == "in-region-speech"


@pytest.mark.asyncio
async def test_naming_no_engine_sends_audio_to_the_agents_own_model(monkeypatch):
    from agent.src.settings import settings

    monkeypatch.setattr(settings, "DICTATION_MODEL", "")
    with patch.object(speech_routes, "_orchestrator_model", return_value="the-agent"):
        assert speech_routes._dictation_model() == "the-agent"


@pytest.mark.asyncio
async def test_the_named_engine_is_the_one_the_recording_reaches(monkeypatch):
    from agent.src.settings import settings

    monkeypatch.setattr(settings, "DICTATION_MODEL", "in-region-speech")
    with patch(
        "agent.src.knowledge.transcribe.transcribe", return_value="said"
    ) as heard:
        speech_routes._to_text("dictation.webm", b"audio")
    assert heard.call_args.args[2] == "in-region-speech"


class TestTheRecordingIsNotKept:
    """E38-T4: audio obeys the same retention rules as text."""

    def test_a_dictation_is_always_too_small_to_be_uploaded(self):
        from agent.src.settings import settings

        assert settings.DICTATION_MAX_BYTES <= settings.TRANSCRIBE_MAX_INLINE_BYTES

    @pytest.mark.asyncio
    async def test_nothing_is_written_to_storage(self, allowed):
        allowed(True)
        with (
            patch("agent.src.knowledge.media_upload.upload_media") as uploaded,
            patch.object(speech_routes, "_to_text", return_value="said something"),
        ):
            await speech_routes.transcribe_dictation(
                request=object(),
                audio=_Upload(b"x" * 1024),  # type: ignore[arg-type]
            )
        assert not uploaded.called

    @pytest.mark.asyncio
    async def test_the_log_carries_a_size_and_not_the_words(self, allowed, caplog):
        allowed(True)
        with patch.object(speech_routes, "_to_text", return_value="my card is 4111"):
            with caplog.at_level("INFO"):
                await speech_routes.transcribe_dictation(
                    request=object(),
                    audio=_Upload(b"x" * 16),  # type: ignore[arg-type]
                )
        assert "4111" not in caplog.text


class TestNothingIsSentOnItsOwn:
    """E38-T2 and T4 together: the transcript goes to the composer."""

    @pytest.mark.asyncio
    async def test_transcribing_starts_no_run(self, allowed):
        allowed(True)
        with patch.object(speech_routes, "_to_text", return_value="hello"):
            answer = await speech_routes.transcribe_dictation(
                request=object(),
                audio=_Upload(),  # type: ignore[arg-type]
            )
        assert set(answer) == {"text"}
        assert answer["text"] == "hello"
