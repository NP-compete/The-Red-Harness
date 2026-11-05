"""Choosing how a document is read, and admitting when it was read badly."""

from __future__ import annotations

import pytest

from agent.src.knowledge.extraction_quality import (
    Attempt,
    Reader,
    ReaderChain,
    register,
)

STANDARD = Reader(name="standard", reports_confidence=True)
FALLBACK = Reader(name="fallback", reports_confidence=True)


def chain(*readers: Reader, floor: float = 0.6) -> ReaderChain:
    return ReaderChain(list(readers) or [STANDARD, FALLBACK], quality_floor=floor)


def test_a_reader_that_cannot_report_confidence_is_refused():
    with pytest.raises(ValueError):
        register(Reader(name="silent", reports_confidence=False))


def test_a_reader_that_reports_confidence_is_accepted():
    assert register(STANDARD) is STANDARD


def test_a_good_first_attempt_is_used():
    result = chain().read(lambda reader: Attempt(text="clean text", confidence=0.9))
    assert result.text == "clean text"
    assert result.reader == "standard"


def test_a_poor_attempt_falls_back_to_the_next_reader():
    attempts = iter(
        [Attempt(text="mush", confidence=0.2), Attempt(text="better", confidence=0.8)]
    )
    result = chain().read(lambda reader: next(attempts))
    assert result.reader == "fallback"
    assert result.text == "better"


def test_the_best_attempt_wins_when_none_clears_the_floor():
    attempts = iter(
        [Attempt(text="bad", confidence=0.2), Attempt(text="less bad", confidence=0.4)]
    )
    result = chain().read(lambda reader: next(attempts))
    assert result.text == "less bad"


def test_a_result_below_the_floor_is_marked_degraded():
    result = chain().read(lambda reader: Attempt(text="mush", confidence=0.2))
    assert result.degraded is True


def test_a_result_above_the_floor_is_not_degraded():
    assert (
        chain().read(lambda reader: Attempt(text="ok", confidence=0.9)).degraded
        is False
    )


def test_a_degraded_result_says_so_in_words():
    result = chain().read(lambda reader: Attempt(text="mush", confidence=0.2))
    assert "confidence" in result.note.lower()


def test_a_good_result_carries_no_note():
    assert chain().read(lambda reader: Attempt(text="ok", confidence=0.9)).note == ""


def test_a_reader_that_fails_outright_is_skipped():
    def attempt(reader):
        if reader.name == "standard":
            raise RuntimeError("engine down")
        return Attempt(text="from fallback", confidence=0.9)

    assert chain().read(attempt).reader == "fallback"


def test_every_reader_failing_is_reported_rather_than_returning_nothing():
    def attempt(reader):
        raise RuntimeError("engine down")

    with pytest.raises(RuntimeError):
        chain().read(attempt)


def test_which_readers_were_tried_is_reported():
    attempts = iter(
        [Attempt(text="mush", confidence=0.2), Attempt(text="better", confidence=0.8)]
    )
    assert chain().read(lambda reader: next(attempts)).tried == ("standard", "fallback")
