"""Replacing a summarised span with the summary that stands in for it."""

from __future__ import annotations

import pytest

from agent.src.agent.compaction import (
    Message,
    apply_compaction,
    plan_compaction,
)


def conversation(n: int = 6, tokens: int = 400) -> list[Message]:
    return [Message(role="system", text="rules", tokens=tokens)] + [
        Message(role="user", text=f"turn {i}", tokens=tokens) for i in range(n)
    ]


def compacted(summary="earlier: three incidents discussed", **kwargs):
    messages = kwargs.pop("messages", conversation())
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    return apply_compaction(messages, plan, summary=summary)


def test_the_summary_replaces_the_span_it_covers():
    result = compacted()
    assert "turn 0" not in [m.text for m in result]
    assert any("earlier:" in m.text for m in result)


def test_the_system_message_stays_first():
    assert compacted()[0].role == "system"


def test_recent_turns_survive_verbatim():
    texts = [m.text for m in compacted()]
    assert texts[-2:] == ["turn 4", "turn 5"]


def test_the_summary_sits_before_what_it_precedes():
    texts = [m.text for m in compacted()]
    assert texts.index("earlier: three incidents discussed") < texts.index("turn 4")


def test_the_summary_is_marked_as_one():
    summary = next(m for m in compacted() if "earlier:" in m.text)
    assert summary.is_summary is True


def test_an_untrusted_span_produces_an_untrusted_summary():
    messages = [
        Message(role="user", text=f"t{i}", tokens=400, trusted=False) for i in range(5)
    ]
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    summary = next(
        m for m in apply_compaction(messages, plan, summary="s") if m.is_summary
    )
    assert summary.trusted is False


def test_a_trusted_span_produces_a_trusted_summary():
    summary = next(m for m in compacted() if m.is_summary)
    assert summary.trusted is True


def test_applying_nothing_changes_nothing():
    messages = conversation(n=1)
    assert apply_compaction(messages, None, summary="unused") == messages


def test_an_empty_summary_is_refused_rather_than_losing_the_span():
    messages = conversation()
    plan = plan_compaction(messages, limit_tokens=1000, keep_recent=2)
    with pytest.raises(ValueError):
        apply_compaction(messages, plan, summary="   ")
