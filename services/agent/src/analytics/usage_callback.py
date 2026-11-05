"""LangChain callback that attributes each model call to its Aegra run."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import ChatGeneration, LLMResult

from agent.src.analytics.usage import record_llm_usage
from agent.src.token_budget.service import (
    extract_cached_tokens,
    extract_tokens_from_llm_result,
    extract_tokens_from_message,
)
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _run_id_from_config() -> str | None:
    """The Aegra run id, from the active LangGraph config."""
    try:
        from langgraph.config import get_config

        configurable = (get_config() or {}).get("configurable") or {}
    except Exception:
        return None
    value = configurable.get("run_id")
    return str(value) if value else None


def _run_id_from_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Fallback for callers that do pass metadata carrying the run id."""
    if not metadata:
        return None
    value = metadata.get("run_id")
    return str(value) if value else None


def _model_from_response(response: LLMResult) -> str | None:
    for generation_list in response.generations:
        for generation in generation_list:
            if not isinstance(generation, ChatGeneration):
                continue
            name = (generation.message.response_metadata or {}).get("model_name")
            if name:
                return str(name)
    llm_output = response.llm_output or {}
    if isinstance(llm_output, dict):
        name = llm_output.get("model_name") or llm_output.get("model")
        if name:
            return str(name)
    return None


class UsageRecorderCallbackHandler(AsyncCallbackHandler):
    """Record tokens and model per completed LLM call."""

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Any = None,
        parent_run_id: Any | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Record token usage once the model call has finished."""
        aegra_run_id = _run_id_from_config() or _run_id_from_metadata(metadata)
        if not aegra_run_id:
            logger.debug("usage_callback_no_run_id")
            return

        input_tokens, output_tokens = extract_tokens_from_llm_result(response)
        if input_tokens <= 0 and output_tokens <= 0:
            input_tokens, output_tokens = _tokens_from_generations(response)

        await record_llm_usage(
            aegra_run_id,
            _model_from_response(response),
            input_tokens,
            output_tokens,
            extract_cached_tokens(response),
        )


def _tokens_from_generations(response: LLMResult) -> tuple[int, int]:
    input_tokens = 0
    output_tokens = 0
    for generation_list in response.generations:
        for generation in generation_list:
            if not isinstance(generation, ChatGeneration):
                continue
            in_t, out_t = extract_tokens_from_message(generation.message)
            input_tokens += in_t
            output_tokens += out_t
    return input_tokens, output_tokens
