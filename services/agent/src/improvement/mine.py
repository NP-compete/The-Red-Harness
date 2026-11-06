"""Signals in a run that configuration could fix."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

DELEGATION = frozenset({"task"})

_BUDGET_NOTICE = re.compile(r"call budget for this \w+ is spent for:\s*([^(\n]+)", re.I)


@dataclass
class Observation:
    """One thing noticed across runs, and how often it was seen."""

    kind: str
    detail: str
    run_id: str
    runs: list[str] = field(default_factory=list)
    seen: int = 0
    last_seen: str | None = None


def mine(runs: list[Any], *, since: str | None = None) -> list[Observation]:
    """Everything worth a person's attention, most frequent first."""
    found: dict[tuple[str, str], list[str]] = defaultdict(list)
    when: dict[tuple[str, str], list[str]] = defaultdict(list)

    for run in runs:
        if not isinstance(run, dict):
            continue
        at = str(run.get("created_at") or "")
        if _older_than(at, since):
            continue
        run_id = str(run.get("run_id") or "")
        messages = run.get("messages")
        if not isinstance(messages, list) or not messages:
            continue
        for kind, detail in _signals(messages):
            found[(kind, detail)].append(run_id)
            if at:
                when[(kind, detail)].append(at)

    observations = [
        Observation(
            kind=kind,
            detail=detail,
            run_id=seen_in[0],
            runs=list(dict.fromkeys(seen_in)),
            seen=len(seen_in),
            last_seen=max(when[(kind, detail)]) if when[(kind, detail)] else None,
        )
        for (kind, detail), seen_in in found.items()
    ]
    return sorted(observations, key=lambda o: (-o.seen, o.kind, o.detail))


def _older_than(at: str, since: str | None) -> bool:
    """Whether a run plainly predates the window."""
    if not since or not at:
        return False

    try:
        return _when(at) < _when(since)
    except (ValueError, TypeError):
        return False


def _when(value: str) -> datetime:
    """A timestamp, always with a zone."""
    from datetime import datetime, timezone

    found = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


def _signals(messages: list[Any]) -> list[tuple[str, str]]:
    """Every signal worth noticing in a conversation."""
    out: list[tuple[str, str]] = []
    out.extend(_unused_results(messages))
    out.extend(_spent_budgets(messages))
    out.extend(_repeated_questions(messages))
    out.extend(_skill_loaded_and_unused(messages))
    return out


def _unused_results(messages: list[Any]) -> list[tuple[str, str]]:
    """A tool answered and the answer went nowhere."""
    out: list[tuple[str, str]] = []

    for index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("type") != "tool":
            continue
        name = str(message.get("name") or "")
        content = _text_of(message.get("content"))
        after = " ".join(
            _text_of(later.get("content"))
            for later in messages[index + 1 :]
            if isinstance(later, dict) and later.get("type") == "ai"
        )

        if not content.strip():
            if name in DELEGATION:
                out.append(("empty_delegation", f"{name} returned nothing"))
            continue

        if name in DELEGATION:
            continue

        if _failed(content):
            out.append(("tool_failed", f"{name} answered with an error"))
            continue

        if not after.strip():
            out.append(("answer_missing", f"{name} answered and the run said nothing"))
            continue

        if _found_nothing(content):
            continue

        if not _mentions(after, content):
            out.append(("tool_abandoned", f"{name} was called and its result unused"))

    return out


SKILLS_PREFIX = "/skills/"

UNNAMED_SKILL = "?"


def _skill_paths(messages: list[Any]) -> dict[str, str]:
    """Tool-call ids that read a skill, mapped to the skill's name."""
    found: dict[str, str] = {}
    for message in messages:
        if not isinstance(message, dict):
            continue
        for call in message.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            name = ""
            for value in (call.get("args") or {}).values():
                text = str(value)
                if SKILLS_PREFIX not in text:
                    continue
                segment = text.split(SKILLS_PREFIX, 1)[1].split("/", 1)[0].strip()
                if segment and not any(c.isspace() for c in segment):
                    name = segment
                    break
            if not name and not any(
                SKILLS_PREFIX in str(v) for v in (call.get("args") or {}).values()
            ):
                continue
            found[str(call.get("id") or "")] = name or UNNAMED_SKILL
    return found


def _skill_loaded_and_unused(messages: list[Any]) -> list[tuple[str, str]]:
    """A skill was read and nothing was done with it (E12-T2.1)."""
    skills = _skill_paths(messages)
    if not skills:
        return []

    last = -1
    name = ""
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("type") != "tool":
            continue
        found = skills.get(str(message.get("tool_call_id") or ""))
        if found:
            last, name = index, found

    if last < 0:
        return []

    for message in messages[last + 1 :]:
        if not isinstance(message, dict) or message.get("type") != "tool":
            continue
        if not skills.get(str(message.get("tool_call_id") or "")):
            return []

    said = "a skill" if name == UNNAMED_SKILL else f"the {name} skill"
    return [("skill_unused", f"{said} was read and nothing followed it")]


def _text_of(content: Any) -> str:
    """The words in a message, whatever shape it arrives in."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or ""))
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(part for part in parts if part)
    return "" if content is None else str(content)


def _distinctive(text: str) -> set[str]:
    """The words in a result worth looking for in an answer."""
    return {
        w
        for w in re.findall(r"[A-Za-z0-9]+", text.lower())
        if len(w) > 2 or w.isdigit()
    }


_FAILED = re.compile(r"^\s*(error|exception|traceback|failed)\b[:\s]", re.I)

_NOTHING = re.compile(
    r"\b(no\s+\w*\s*(files?|results?|matches?|rows?|records?|documents?)\s*(found|returned)?"
    r"|not\s+found|nothing\s+found|no\s+results|empty)\b",
    re.I,
)
_SHORT = 80


def _failed(result: str) -> bool:
    """Whether the tool answered with a failure rather than a result."""
    return bool(_FAILED.search(result))


_ACKNOWLEDGED = re.compile(
    r"^\s*(successfully|done|ok|updated|created|written|wrote|saved|deleted)\b", re.I
)


def _found_nothing(result: str) -> bool:
    """Whether the tool ran correctly and had nothing to report."""
    text = result.strip()
    if _ACKNOWLEDGED.search(text):
        return True
    return len(text) <= _SHORT and bool(_NOTHING.search(result))


def _mentions(said: str, result: str) -> bool:
    """Whether what was said afterwards drew on the result at all."""
    words = _distinctive(result)
    if not words:
        return True
    spoken = set(re.findall(r"[A-Za-z0-9]+", said.lower()))
    return bool(words & spoken)


def _spent_budgets(messages: list[Any]) -> list[tuple[str, str]]:
    """The budget-exhausted signal, if the conversation shows one."""
    for message in messages:
        if not isinstance(message, dict):
            continue
        found = _BUDGET_NOTICE.search(_text_of(message.get("content")))
        if found:
            return [("budget_spent", f"ran out of calls for: {found.group(1).strip()}")]
    return []


def _repeated_questions(messages: list[Any]) -> list[tuple[str, str]]:
    """The agent asked, was answered, and asked again."""
    asked: list[str] = []
    for message in messages:
        if not isinstance(message, dict) or message.get("type") != "ai":
            continue
        said = _text_of(message.get("content")).strip()
        if said.endswith("?"):
            asked.append(said.lower())

    for question in asked:
        if asked.count(question) > 1:
            return [("repeated_question", "the same question was asked more than once")]
    return []
