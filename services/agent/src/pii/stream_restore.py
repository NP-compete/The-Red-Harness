"""Put substituted values back while the answer is still streaming."""

from collections.abc import Iterator
from typing import Any


class StreamingRestorer:
    """Restore placeholders across chunk boundaries for one message."""

    def __init__(self, token_map: dict[str, str]) -> None:
        """Start with `token_map`, holding nothing back yet."""
        self._token_map = token_map
        self._known = -1
        self._tokens: list[str] = []
        self._longest = 0
        self._held = ""

    def _sync(self) -> None:
        """Re-sort the tokens if the map has grown since last time."""
        if len(self._token_map) == self._known:
            return
        self._tokens = sorted(self._token_map, key=len, reverse=True)
        self._longest = max((len(token) for token in self._tokens), default=0)
        self._known = len(self._token_map)

    def feed(self, text: str) -> str:
        """Return the part of `text` that is safe to emit now."""
        self._sync()
        if not self._token_map:
            return text

        buffer = self._restore(self._held + text)
        cut = self._pending_at(buffer)
        self._held = buffer[cut:]
        return buffer[:cut]

    def flush(self) -> str:
        """Return whatever was held back; the message is over."""
        self._sync()
        held, self._held = self._held, ""
        return self._restore(held)

    def _restore(self, text: str) -> str:
        """Put the real values back in place of any tokens in `text`."""
        for token in self._tokens:
            if token in text:
                text = text.replace(token, self._token_map[token])
        return text

    def _pending_at(self, text: str) -> int:
        """Where the tail that might still complete a placeholder starts."""
        start = text.rfind("[")
        if start == -1 or "]" in text[start:]:
            return len(text)
        return len(text) if len(text) - start > self._longest else start


class StreamRestorers:
    """One restorer per message in flight, plus the means to drain them."""

    def __init__(self, token_map: dict[str, str]) -> None:
        """Start with `token_map` and no messages seen."""
        self._token_map = dict(token_map)
        self._by_message: dict[Any, StreamingRestorer] = {}
        self._last_item: dict[Any, Any] = {}

    def refresh(self, token_map: dict[str, str]) -> None:
        """Take in placeholders assigned since the stream began."""
        self._token_map.update(token_map)

    def for_message(self, message_id: Any) -> StreamingRestorer:
        """The restorer for `message_id`, making one if needed."""
        restorer = self._by_message.get(message_id)
        if restorer is None:
            restorer = StreamingRestorer(self._token_map)
            self._by_message[message_id] = restorer
        return restorer

    def restore_once(self, text: str) -> str:
        """Restore text that arrives whole, with nothing held back."""
        restorer = StreamingRestorer(self._token_map)
        return restorer.feed(text) + restorer.flush()

    def remember(self, message_id: Any, item: Any) -> None:
        """Remember the last item seen for `message_id`."""
        self._last_item[message_id] = item

    def flush(self) -> Iterator[Any]:
        """Yield a final item per message that still has text held back."""
        for message_id, restorer in self._by_message.items():
            tail = restorer.flush()
            if not tail:
                continue
            last = self._last_item.get(message_id)
            if last is None:
                continue
            chunk, metadata = last
            yield (chunk.model_copy(update={"content": tail}), metadata)
        self._by_message.clear()
        self._last_item.clear()


def restore_stream_item(data: Any, restorers: StreamRestorers) -> Any:
    """Restore placeholders in one messages-mode stream item."""
    if not isinstance(data, (list, tuple)) or len(data) != 2:
        return data

    chunk, metadata = data
    if not hasattr(chunk, "content"):
        return data

    update: dict[str, Any] = {}
    if isinstance(chunk.content, str):
        restorer = restorers.for_message(getattr(chunk, "id", None))
        update["content"] = restorer.feed(chunk.content)

    tool_calls = getattr(chunk, "tool_calls", None) or []
    if tool_calls:
        update["tool_calls"] = [
            {
                **call,
                "args": {
                    key: restorers.restore_once(value)
                    if isinstance(value, str)
                    else value
                    for key, value in (call.get("args") or {}).items()
                },
            }
            for call in tool_calls
        ]

    if not update:
        return data

    restored = (chunk.model_copy(update=update), metadata)
    restorers.remember(getattr(chunk, "id", None), restored)
    return restored
