"""Why an answer looks the way it does."""

from __future__ import annotations

from typing import Any

_MODEL_KEYS = ("model_name", "model", "model_version")
_FINISH_KEYS = ("finish_reason", "finishReason", "stop_reason")

_TRUNCATED = {"max_tokens", "maxtokens", "length", "max_output_tokens"}


def _first(meta: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _is_truncated(finish_reason: str) -> bool:
    return finish_reason.lower().replace("-", "_") in _TRUNCATED


def describe_message(msg: Any) -> dict[str, Any]:
    """Provenance for one AI message, or `{}` when there is nothing to say."""
    meta = getattr(msg, "response_metadata", None)
    if not isinstance(meta, dict):
        meta = {}
    extra = getattr(msg, "additional_kwargs", None)
    if not isinstance(extra, dict):
        extra = {}

    out: dict[str, Any] = {}

    auth_required = extra.get("auth_required")
    if isinstance(auth_required, list) and auth_required:
        out["auth_required"] = auth_required

    notes = extra.get("answer_notes")
    if isinstance(notes, dict):
        figures = notes.get("figures")
        flagged = isinstance(figures, dict) and figures.get("unsupported")
        shaky = notes.get("stance") not in (None, "plain")
        looped = bool(notes.get("loop"))
        coverage = notes.get("coverage")
        missed = isinstance(coverage, dict) and not coverage.get("complete", True)
        unbacked = bool(notes.get("claims"))
        planted = bool(notes.get("injection"))
        withheld = bool(notes.get("budget"))
        if flagged or shaky or looped or missed or unbacked or planted or withheld:
            out["answer_notes"] = notes

    model = _first(meta, _MODEL_KEYS)
    if model:
        out["model"] = model

    finish_reason = _first(meta, _FINISH_KEYS)
    if finish_reason:
        out["finish_reason"] = finish_reason
        if _is_truncated(finish_reason):
            out["truncated"] = True

    for key in ("routed_tier", "routed_by", "fallback_from", "cached", "pii_scrubbed"):
        value = extra.get(key)
        if value not in (None, "", False):
            out[key] = value

    content = getattr(msg, "content", None)
    if not content and not getattr(msg, "tool_calls", None):
        out["empty"] = True

    return out
