"""Outermost graph wrapper for PII token-map sharing and SSE stream restoration."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, cast

from langchain_core.messages.tool import ToolCallChunk

from agent.src.pii.stream_restore import StreamRestorers, restore_stream_item
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _preview(value: Any, max_len: int = 120) -> str:
    if isinstance(value, str):
        return value[:max_len]
    return repr(value)[:max_len]


def _restore_text(text: Any, container: dict[str, str]) -> Any:
    if not isinstance(text, str) or not container:
        return text
    for token, value in container.items():
        if token in text:
            text = text.replace(token, value)
    return text


def _restore_content(content: Any, container: dict[str, str]) -> Any:
    if isinstance(content, str):
        return _restore_text(content, container)
    if isinstance(content, list):
        result = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                result.append(
                    {**block, "text": _restore_text(block.get("text", ""), container)}
                )
            else:
                result.append(block)
        return result
    return content


def _restore_args(args: Any, container: dict[str, str]) -> Any:
    if isinstance(args, dict):
        return {k: _restore_args(v, container) for k, v in args.items()}
    if isinstance(args, list):
        return [_restore_args(v, container) for v in args]
    if isinstance(args, str):
        return _restore_text(args, container)
    return args


def _restore_message_stream_data(data: Any, container: dict[str, str]) -> Any:
    """Restore tokens in a LangGraph messages-mode stream item."""
    if not container:
        return data

    if isinstance(data, (list, tuple)) and len(data) == 2:
        chunk, metadata = data
        if hasattr(chunk, "content"):
            restored_content = _restore_content(chunk.content, container)
            tool_calls = getattr(chunk, "tool_calls", None) or []
            if tool_calls:
                restored_tcs = [
                    {**tc, "args": _restore_args(tc.get("args", {}), container)}
                    for tc in tool_calls
                ]
                chunk = chunk.model_copy(
                    update={"content": restored_content, "tool_calls": restored_tcs}
                )
            elif restored_content != chunk.content:
                chunk = chunk.model_copy(update={"content": restored_content})
        result = [chunk, metadata]
        return tuple(result) if isinstance(data, tuple) else result

    return _restore_args(data, container)


class PIIAwareRunnable:
    """Outermost graph wrapper that manages the PII token map across requests."""

    def __init__(self, runnable: Any) -> None:
        """Wrap *runnable* with PII token-map management."""
        self._runnable = runnable

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped runnable."""
        return getattr(self._runnable, name)

    def copy(self, **kwargs: Any) -> "PIIAwareRunnable":
        """Return a re-wrapped copy of the inner runnable."""
        return PIIAwareRunnable(self._runnable.copy(**kwargs))

    def with_config(self, config: Any = None, **kwargs: Any) -> "PIIAwareRunnable":
        """Re-wrap after with_config so the PIIAwareRunnable is not stripped by __getattr__."""
        if config is not None:
            inner = self._runnable.with_config(config, **kwargs)
        else:
            inner = self._runnable.with_config(**kwargs)
        return PIIAwareRunnable(inner)

    def _setup_container(self) -> tuple[dict[str, str], bool]:
        """Return the shared token-map container, registering one if needed."""
        try:
            from agent.src.pii import get_scrubber

            s = get_scrubber()
            if not s:
                logger.debug(
                    "pii_aware_runnable scrubber_not_found — PII middleware inactive"
                )
                return {}, False
            existing = s._get_shared_container()
            if existing is not None:
                logger.debug("pii_aware_runnable container_reused (nested runnable)")
                return existing, False
            container: dict[str, str] = {}
            s.set_shared_container(container)
            logger.debug("pii_aware_runnable container_registered=True")
            return container, True
        except Exception as exc:
            logger.warning("pii_aware_runnable container_setup_failed: %s", exc)
            return {}, False

    def _clear_container(self, owned: bool) -> None:
        """Clear the instance-level container reference on the scrubber after a request."""
        if not owned:
            return
        try:
            from agent.src.pii import get_scrubber

            s = get_scrubber()
            if s and getattr(s, "_instance_container", None) is not None:
                s._instance_container = None
        except Exception:
            pass

    def _assemble_chunk(self, events: list[dict]) -> Any:
        """Sum the AIMessageChunk objects from one run's buffered events into one."""
        assembled = None
        for e in events:
            chunk = e.get("data", {}).get("chunk")
            if chunk is None:
                continue
            assembled = chunk if assembled is None else assembled + chunk
        return assembled

    def _restore_chunk(self, chunk: Any, container: dict[str, str]) -> Any:
        """Return a new AIMessageChunk with content and tool_calls fully restored."""
        from langchain_core.messages import AIMessageChunk

        content = _restore_content(getattr(chunk, "content", None), container)
        tool_calls = getattr(chunk, "tool_calls", None) or []
        if not tool_calls:
            return AIMessageChunk(content=content)

        restored_tool_calls = [
            {**tc, "args": _restore_args(tc.get("args", {}), container)}
            for tc in tool_calls
        ]
        tool_call_chunks = [
            {
                "name": tc.get("name"),
                "args": json.dumps(tc.get("args", {})),
                "id": tc.get("id"),
                "index": i,
            }
            for i, tc in enumerate(restored_tool_calls)
        ]
        return AIMessageChunk(
            content=content,
            tool_call_chunks=cast("list[ToolCallChunk]", tool_call_chunks),
        )

    async def _flush_run(
        self, run_id: Any, events: list[dict], container: dict[str, str]
    ) -> AsyncIterator[Any]:
        """Assemble, restore, and yield one LLM run's buffered chunks as a single event."""
        if not events:
            return
        assembled = self._assemble_chunk(events)
        last = events[-1]
        if assembled is None or not container:
            for e in events:
                yield e
            return
        restored = self._restore_chunk(assembled, container)
        logger.debug(
            "pii_aware_runnable sse_restore run_id=%s chunks=%d tool_calls=%d",
            run_id,
            len(events),
            len(restored.tool_calls or []),
        )
        yield {**last, "data": {"chunk": restored}}

    def _restore_tool_event_args(self, event: dict, container: dict[str, str]) -> dict:
        """Restore args on an on_tool_start event before it reaches the client."""
        if not container:
            return event
        data = event.get("data", {})
        tool_input = data.get("input")
        if isinstance(tool_input, dict) and "args" in tool_input:
            restored_input = {
                **tool_input,
                "args": _restore_args(tool_input["args"], container),
            }
            return {**event, "data": {**data, "input": restored_input}}
        if isinstance(tool_input, dict):
            return {
                **event,
                "data": {**data, "input": _restore_args(tool_input, container)},
            }
        return event

    def _restore_tool_event_output(
        self, event: dict, container: dict[str, str]
    ) -> dict:
        """Restore tokens in an on_tool_end event's output before it reaches the client."""
        if not container:
            return event
        data = event.get("data", {})
        output = data.get("output")
        if output is None:
            return event
        restored_output = _restore_args(output, container)
        return {**event, "data": {**data, "output": restored_output}}

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        """Invoke the wrapped runnable with PII container management."""
        _container, owned = self._setup_container()
        try:
            return await self._runnable.ainvoke(input, config, **kwargs)
        finally:
            self._clear_container(owned)

    async def astream(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        """Stream chunks from the wrapped runnable, restoring PII tokens in message events."""
        container, owned = self._setup_container()
        thread_id: str | None = (config or {}).get("configurable", {}).get("thread_id")

        def _token_map() -> dict[str, str]:
            if thread_id:
                try:
                    from agent.src.pii.scrubber import _thread_token_maps

                    merged = dict(container)
                    merged.update(_thread_token_maps.get(thread_id, {}))
                    return merged
                except Exception:
                    pass
            return container

        restorers: StreamRestorers | None = None

        namespace: tuple = ()

        async for chunk in self._runnable.astream(input, config, **kwargs):
            if isinstance(chunk, tuple) and len(chunk) in (2, 3):
                prefix = chunk[:-2]
                mode, data = chunk[-2], chunk[-1]
                if mode == "messages":
                    tok_map = _token_map()
                    if tok_map:
                        if restorers is None:
                            restorers = StreamRestorers(tok_map)
                        else:
                            restorers.refresh(tok_map)
                        data = restore_stream_item(data, restorers)
                        data = _restore_message_stream_data(data, tok_map)
                    namespace = prefix
                    yield (*prefix, mode, data)
                    continue
            yield chunk

        if restorers is not None:
            for held in restorers.flush():
                yield (*namespace, "messages", held)

        self._clear_container(owned)

    async def astream_events(
        self, input: Any, config: Any = None, **kwargs: Any
    ) -> Any:
        """Stream events from the wrapped runnable, restoring PII tokens before emission."""
        container, owned = self._setup_container()

        thread_id: str | None = (config or {}).get("configurable", {}).get("thread_id")

        def _token_map() -> dict[str, str]:
            """Return the best available token map at yield time."""
            if thread_id:
                try:
                    from agent.src.pii.scrubber import _thread_token_maps

                    merged = dict(container)
                    merged.update(_thread_token_maps.get(thread_id, {}))
                    return merged
                except Exception:
                    pass
            return container

        buffers: dict[Any, list[dict]] = {}

        async for event in self._runnable.astream_events(input, config, **kwargs):
            event_type = event.get("event", "")
            run_id = event.get("run_id")

            if event_type == "on_chat_model_stream":
                buffers.setdefault(run_id, []).append(event)
                continue

            if event_type in ("on_chat_model_end", "on_llm_end") and run_id in buffers:
                async for restored_event in self._flush_run(
                    run_id, buffers.pop(run_id), _token_map()
                ):
                    yield restored_event
                yield event
                continue

            if event_type == "on_tool_start":
                event = self._restore_tool_event_args(event, _token_map())

            elif event_type == "on_tool_end":
                event = self._restore_tool_event_output(event, _token_map())

            yield event

        for run_id, events in buffers.items():
            async for restored_event in self._flush_run(run_id, events, _token_map()):
                yield restored_event

        self._clear_container(owned)
