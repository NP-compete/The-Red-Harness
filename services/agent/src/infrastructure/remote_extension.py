"""An extension that runs somewhere else (E37-T3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.src.security.circuit_breaker import Breakers, State
from agent.src.security.extensions import (
    HookPoint,
    Payload,
    Refused,
    Rewritten,
    Unchanged,
    read_outcome,
)
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

DEFAULT_TIMEOUT_SECONDS = 2.0

BREAKER_THRESHOLD = 3
BREAKER_COOLDOWN_SECONDS = 60

POINTS = tuple(point.value for point in HookPoint)

DEFAULT_POINTS = ("before_model",)

_breakers = Breakers(
    threshold=BREAKER_THRESHOLD, cooldown_seconds=BREAKER_COOLDOWN_SECONDS
)


class ExtensionRefused(RuntimeError):
    """The extension said no, or a required one could not answer."""

    def __init__(self, name: str, reason: str) -> None:
        """Record which extension refused, and why."""
        self.name, self.reason = name, reason
        super().__init__(f"{name}: {reason}")


@dataclass(frozen=True)
class RemoteExtension:
    """One HTTP extension, as configuration declares it."""

    name: str
    url: str
    required: bool = True
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    points: tuple[str, ...] = DEFAULT_POINTS

    def asked_at(self, point: str) -> bool:
        """Whether this extension is consulted at `point`."""
        return point in self.points

    def unavailable(self) -> bool:
        """Whether this extension's breaker is open."""
        return _breakers.state(self.name) is State.OPEN

    async def apply(
        self,
        text: str,
        *,
        point: str = "before_model",
        tool: str | None = None,
        subject: str | None = None,
    ) -> str:
        """The text after this extension, or raise if it refused."""
        if self.unavailable():
            return self._gave_up(text, "it has been failing and is being left alone")

        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url,
                    json=Payload(
                        text=text,
                        tool=tool,
                        subject=subject,
                        point=HookPoint(point),
                    ).as_json(),
                )
            if response.status_code >= 400:
                raise RuntimeError(f"it answered {response.status_code}")
            body = response.json()
        except ExtensionRefused:
            raise
        except Exception as error:
            _breakers.failed(self.name)
            return self._gave_up(text, str(error))

        _breakers.succeeded(self.name)
        return self._read(body, text)

    def _read(self, body: Any, text: str) -> str:
        """Read the extension's verdict, falling back if there is none."""
        outcome = read_outcome(body)

        if outcome is None:
            _breakers.failed(self.name)
            return self._gave_up(text, "it did not answer with a verdict")

        if isinstance(outcome, Refused):
            raise ExtensionRefused(self.name, outcome.reason)

        if isinstance(outcome, Rewritten):
            return outcome.text

        assert isinstance(outcome, Unchanged)
        return text

    def _gave_up(self, text: str, why: str) -> str:
        """Fail-open returns the text it was given, untouched."""
        if self.required:
            raise ExtensionRefused(
                self.name,
                f"this check could not run ({why}), and this deployment "
                "refuses rather than continuing without it",
            )
        logger.warning(
            "Optional extension '%s' did not run and was skipped: %s", self.name, why
        )
        return text


def declared_remote(entry: dict[str, Any]) -> RemoteExtension:
    """Read one declared HTTP extension, refusing anything ambiguous."""
    url = str(entry.get("url") or "").strip()
    if not url:
        raise ValueError("Every remote extension needs a url")
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"'{url}' is not an http(s) url")

    mode = str(entry.get("on_failure", "closed")).strip().lower()
    if mode not in ("closed", "open"):
        raise ValueError(
            f"'{mode}' is not a usable on_failure for '{url}' — use 'closed' "
            "to refuse without it, or 'open' to carry on"
        )

    asked = entry.get("points") or list(DEFAULT_POINTS)
    if isinstance(asked, str) or not isinstance(asked, (list, tuple)):
        raise ValueError(
            f"points for '{url}' is a list of {', '.join(POINTS)}, not "
            f"{type(asked).__name__}"
        )
    points = tuple(str(p).strip() for p in asked)
    unknown = [p for p in points if p not in POINTS]
    if unknown:
        raise ValueError(
            f"'{unknown[0]}' is not an extension point for '{url}' — "
            f"the points are {', '.join(POINTS)}"
        )

    timeout = entry.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    try:
        seconds = float(timeout)
    except (TypeError, ValueError):
        raise ValueError(f"'{timeout}' is not a number of seconds") from None
    if seconds <= 0:
        raise ValueError("a timeout of zero seconds never lets anything answer")

    return RemoteExtension(
        name=str(entry.get("name") or url),
        url=url,
        required=mode == "closed",
        timeout_seconds=seconds,
        points=points,
    )


def build_remote_extension_middleware(extensions: list[RemoteExtension]) -> Any | None:
    """One middleware applying every declared remote extension."""
    if not extensions:
        return None

    try:
        from langchain.agents.middleware import AgentMiddleware
    except ImportError:  # pragma: no cover - exercised only without langchain
        logger.warning("Remote extensions declared but langchain is not installed")
        return None

    def _for(point: str) -> list[RemoteExtension]:
        """The extensions consulted at `point`."""
        return [e for e in extensions if e.asked_at(point)]

    def _last_human(request: Any) -> Any | None:
        """The most recent human message in the request, if any."""
        for message in reversed(list(getattr(request, "messages", []) or [])):
            if getattr(message, "type", None) == "human":
                return message
        return None

    async def _through(
        point: str, text: str, *, tool: str | None, subject: str | None
    ) -> str:
        """Pass `text` through every extension consulted at `point`."""
        for extension in _for(point):
            text = await extension.apply(text, point=point, tool=tool, subject=subject)
        return text

    class RemoteExtensionMiddleware(AgentMiddleware):
        """Runs the configured remote extensions around model and tool calls."""

        async def awrap_model_call(self, request: Any, handler: Any) -> Any:
            """Pass the prompt through the before-model extensions, then call."""
            subject = _subject_of(request)
            message = _last_human(request)
            text = getattr(message, "content", None)
            if message is not None and isinstance(text, str) and _for("before_model"):
                changed = await _through(
                    "before_model", text, tool=None, subject=subject
                )
                if changed != text:
                    message.content = changed

            response = await handler(request)

            if not _for("after_model"):
                return response
            return await _rewrite_response(response, subject)

        async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
            """Pass the call through the extensions, refusing if one says no."""
            import json

            subject = _subject_of(request)
            call = getattr(request, "tool_call", None) or {}
            name = call.get("name") if isinstance(call, dict) else None

            if _for("before_tool") and isinstance(call, dict):
                try:
                    said = await _through(
                        "before_tool",
                        json.dumps(call.get("args") or {}, default=str),
                        tool=name,
                        subject=subject,
                    )
                except ExtensionRefused as refused:
                    return _refusal_message(call, refused)
                rewritten = _args_from(said)
                if rewritten is not None and rewritten != call.get("args"):
                    call["args"] = rewritten

            result = await handler(request)

            if not _for("after_tool"):
                return result
            text = getattr(result, "content", None)
            if not isinstance(text, str):
                return result
            try:
                changed = await _through("after_tool", text, tool=name, subject=subject)
            except ExtensionRefused as refused:
                return _refusal_message(call if isinstance(call, dict) else {}, refused)
            if changed != text:
                result.content = changed
            return result

    async def _rewrite_response(response: Any, subject: str | None) -> Any:
        """Put the reply through, where there is a reply to put through."""
        messages = getattr(response, "result", None) or []
        for message in messages:
            text = getattr(message, "content", None)
            if not isinstance(text, str) or not text:
                continue
            changed = await _through("after_model", text, tool=None, subject=subject)
            if changed != text:
                message.content = changed
        return response

    def _args_from(said: str) -> dict | None:
        """The rewritten arguments, or None if they are not usable."""
        import json

        try:
            found = json.loads(said)
        except Exception:
            return None
        return found if isinstance(found, dict) else None

    def _refusal_message(call: dict, refused: ExtensionRefused) -> Any:
        """The tool message explaining that an extension refused the call."""
        from langchain_core.messages import ToolMessage

        return ToolMessage(
            content=(
                f"This call was refused by the '{refused.name}' extension: "
                f"{refused.reason}"
            ),
            tool_call_id=str(call.get("id") or ""),
            name=str(call.get("name") or ""),
            status="error",
        )

    logger.info(
        "Remote extensions in the path: %s",
        ", ".join(
            f"{e.name} ({'required' if e.required else 'optional'}: "
            f"{', '.join(e.points)})"
            for e in extensions
        ),
    )
    return RemoteExtensionMiddleware()


def _subject_of(request: Any) -> str | None:
    """Who the turn is for, if the request carries it."""
    for holder in (getattr(request, "runtime", None), request):
        found = getattr(getattr(holder, "context", None), "user_id", None)
        if isinstance(found, str) and found:
            return found
    return None


def declared_remotes(entries: list[Any]) -> list[RemoteExtension]:
    """The remote extensions among the declared ones."""
    found: list[RemoteExtension] = []
    for entry in entries or []:
        if isinstance(entry, dict) and entry.get("url"):
            found.append(declared_remote(entry))
    return found
