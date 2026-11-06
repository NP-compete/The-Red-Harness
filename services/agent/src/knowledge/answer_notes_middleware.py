"""Stamping an answer with what its figures rest on."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

from agent.src.agent.answer_confidence import Signals, decide_stance
from agent.src.agent.loop_detection import Call, Pattern, inspect_calls
from agent.src.knowledge.coverage import check_coverage
from agent.src.knowledge.numeric_check import check_numbers
from agent.src.knowledge.question_split import split_question
from agent.src.knowledge.support import Claim, Passage, check_support
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])[\s\n]+(?=[\"\'(\[]?[A-Z0-9])")
_HAS_WORD = re.compile(r"[A-Za-z]")


def _read_in_turn(messages: Any) -> list[str]:
    """The text of everything the turn read."""
    return [text for _source, text in _read_with_sources(messages)]


def _read_with_sources(messages: Any) -> list[tuple[str, str]]:
    """What the turn read, each with the tool it came back from."""
    read: list[tuple[str, str]] = []
    for message in messages or []:
        if getattr(message, "type", None) != "tool":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            read.append((getattr(message, "name", "") or "a source", content))
    return read


def _nearest_match(claim: str, read: list[tuple[str, str]]) -> dict[str, Any] | None:
    """The passage closest to a sentence nothing backs up."""
    from agent.src.knowledge.quote_selection import Passage, choose_quote

    best: dict[str, Any] | None = None
    best_overlap = 1
    wanted = _words(claim)
    if not wanted:
        return None

    for source, text in read:
        overlap = len(wanted & _words(text))
        if overlap <= best_overlap:
            continue
        try:
            quote = choose_quote(Passage(source=source, text=text), claim=claim)
        except ValueError:
            continue
        if quote is None:
            continue
        best_overlap = overlap
        best = {
            "source": quote.source,
            "text": quote.text,
            "offset": quote.offset,
            "shortened": quote.shortened,
        }
    return best


def _words(text: str) -> set[str]:
    """The words of `text` worth matching on."""
    return {word for word in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(word) > 2}


def _planted_instructions(read: list[str]) -> dict[str, Any] | None:
    """Signals that something read was written to be obeyed, not read."""
    from agent.src.security.injection_signals import inspect

    signals: list[str] = []
    evidence: list[str] = []
    for text in read:
        report = inspect(text)
        for signal, quote in zip(report.signals, report.evidence, strict=True):
            if signal.value in signals:
                continue
            signals.append(signal.value)
            evidence.append(quote)

    if not signals:
        return None
    return {"signals": signals, "evidence": evidence}


def _stamp(
    message: Any,
    read: list[str],
    asked: str,
    calls: list[Call],
    sources: list[tuple[str, str]] | None = None,
) -> None:
    """Write the notes for this answer onto the message."""
    text = getattr(message, "text", None)
    if not isinstance(text, str) or not text.strip():
        return

    sources = sources if sources is not None else [("a source", one) for one in read]

    checked = check_numbers(text, read=read)
    covered = _coverage(asked, text)
    support = _support(text, read)
    stated = _stance(text, read, asked, covered, support)

    extra = getattr(message, "additional_kwargs", None)
    if not isinstance(extra, dict):
        extra = {}
        message.additional_kwargs = extra

    notes: dict[str, Any] = {
        "figures": {"checked": checked.checked, "unsupported": checked.unsupported},
        "stance": stated.stance.value,
        "hedge": stated.hedge,
        "concerns": stated.concerns,
    }

    planted = _planted_instructions(read)
    if planted is not None:
        notes["injection"] = planted

    if support is not None:
        notes["claims"] = [
            {
                "text": claim.text,
                "supported": claim.supported,
                "contradicted": claim.contradicted,
                "nearest": _nearest_match(claim.text, sources),
            }
            for claim in support.claims
            if not claim.supported
        ]

    if covered is not None and not covered.complete:
        notes["coverage"] = {
            "complete": covered.complete,
            "uncovered": list(covered.uncovered),
            "unused": list(covered.unused),
            "share": covered.share,
            "part_count": len(covered.covered_by),
        }

    looped = inspect_calls(calls) if calls else None
    if looped is not None and looped.pattern is not Pattern.PROGRESSING:
        notes["loop"] = {
            "pattern": looped.pattern.value,
            "should_stop": looped.should_stop,
            "repeated": looped.repeated,
            "times": looped.times,
            "reason": looped.reason,
        }

    already = extra.get("answer_notes")
    if isinstance(already, dict):
        already.update(notes)
    else:
        extra["answer_notes"] = notes


def _calls_in_turn(messages: Any) -> list[Call]:
    """Tool calls the turn made, paired with what came back."""
    results: dict[str, str] = {}
    for message in messages or []:
        if getattr(message, "type", None) == "tool":
            call_id = getattr(message, "tool_call_id", "")
            content = getattr(message, "content", "")
            results[call_id] = content if isinstance(content, str) else ""

    calls = []
    for message in messages or []:
        for call in getattr(message, "tool_calls", None) or []:
            name = call.get("name", "") if isinstance(call, dict) else ""
            args = call.get("args", {}) if isinstance(call, dict) else {}
            call_id = call.get("id", "") if isinstance(call, dict) else ""
            if not name:
                continue
            calls.append(
                Call(
                    tool=name,
                    arguments=json.dumps(args, sort_keys=True, default=str),
                    result=results.get(call_id, "ok"),
                )
            )
    return calls


def _asked(messages: Any) -> str:
    """The most recent human message, as text."""
    for message in reversed(list(messages or [])):
        if getattr(message, "type", None) == "human":
            content = getattr(message, "content", "")
            return content if isinstance(content, str) else ""
    return ""


def _coverage(asked: str, answer: str) -> Any | None:
    """What the answer went near, or None when the question cannot be read."""
    if not asked.strip():
        return None
    try:
        parts = split_question(asked).parts
    except ValueError:
        return None
    if not parts:
        return None
    return check_coverage(parts, found=(answer,))


def _support(text: str, read: list[str]) -> Any:
    """How well the answer's sentences are supported by what was read."""
    passages = (Passage(source="read", text="\n".join(read)),)
    claims = [
        Claim(text=sentence, cites=("read",))
        for raw in _SENTENCE_BREAK.split(text)
        if (sentence := raw.strip()) and _HAS_WORD.search(sentence)
    ]
    return check_support(claims, passages=passages) if claims else None


def _stance(
    text: str,
    read: list[str],
    asked: str = "",
    covered: Any = None,
    support: Any = None,
) -> Any:
    """The stance to take, given coverage and support."""
    return decide_stance(
        Signals(
            coverage=covered.share if covered else 1.0,
            claims_supported=support.supported_share if support else 1.0,
            sources=len(read),
            sources_disagree=bool(support and support.contradicted),
            oldest_source_days=0,
            freshness_matters=False,
            built_on_untrusted=False,
        )
    )


def build_answer_notes_middleware() -> Any:
    """Middleware that notes how well an answer is grounded."""

    class AnswerNotesMiddleware(AgentMiddleware):
        """Record which figures in an answer appear in what was read."""

        async def awrap_model_call(self, request: Any, handler: Any) -> Any:
            """Call the model, then note how grounded the answer is."""
            return self._note(request, await handler(request))

        def wrap_model_call(self, request: Any, handler: Any) -> Any:
            """Call the model, then note how grounded the answer is."""
            return self._note(request, handler(request))

        @staticmethod
        def _note(request: Any, response: Any) -> Any:
            """Note how grounded `response` is, given what the turn read."""
            try:
                sources = _read_with_sources(getattr(request, "messages", None))
                read = [text for _name, text in sources]
                if not read:
                    return response

                message: Any = getattr(response, "result", None)
                if isinstance(message, list):
                    message = message[0] if message else None
                if message is not None:
                    messages = getattr(request, "messages", None)
                    _stamp(
                        message,
                        read,
                        _asked(messages),
                        _calls_in_turn(messages),
                        sources,
                    )
            except Exception:
                logger.debug("Could not take answer notes", exc_info=True)
            return response

    return AnswerNotesMiddleware()
