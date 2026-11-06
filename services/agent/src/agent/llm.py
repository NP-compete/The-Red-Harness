"""LLM factory for creating configured model instances."""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from pydantic import SecretStr

from agent.src.error_handling import llm_retry
from agent.src.exceptions import LLMError
from agent.src.settings import settings
from agent.utils.google_creds import get_service_account_credentials
from agent.utils.pylogger import get_python_logger

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)

_DEFAULT_MAX_OUTPUT_TOKENS: int = settings.MAX_OUTPUT_TOKENS


def is_vertex_model(model_name: str) -> bool:
    """True for Vertex-hosted Gemini and Claude names."""
    return model_name.lower().startswith(settings.vertex_model_prefixes)


def is_claude_model(model_name: str) -> bool:
    """True for Claude on Vertex Model Garden, which has its own client."""
    return model_name.lower().startswith(settings.claude_model_prefixes)


def is_openai_model(model_name: str) -> bool:
    """Does this model name belong to OpenAI rather than another provider?"""
    return model_name.lower().startswith(settings.openai_model_prefixes)


_THRESHOLD_MAP = {v.name: v for v in HarmBlockThreshold}

safety_settings = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: _THRESHOLD_MAP[
        settings.SAFETY_DANGEROUS_CONTENT
    ],
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: _THRESHOLD_MAP[settings.SAFETY_HATE_SPEECH],
    HarmCategory.HARM_CATEGORY_HARASSMENT: _THRESHOLD_MAP[settings.SAFETY_HARASSMENT],
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: _THRESHOLD_MAP[
        settings.SAFETY_SEXUALLY_EXPLICIT
    ],
}


def _thinking_budget() -> int | None:
    """How many tokens the model may spend reasoning before it answers."""
    budget = settings.THINKING_BUDGET
    return None if budget < 0 else budget


@llm_retry
def create_model(
    model_name: str,
    temperature: float = 0.0,
    max_output_tokens: int | None = None,
    thinking_budget: int | None = None,
) -> BaseChatModel:
    """Create a model instance (Vertex AI, or vLLM/OpenAI-compatible)."""
    if not model_name or not model_name.strip():
        raise ValueError("model_name cannot be empty")

    max_output_tokens = max_output_tokens or _DEFAULT_MAX_OUTPUT_TOKENS

    is_gemini = is_vertex_model(model_name) and not is_claude_model(model_name)
    is_claude = is_claude_model(model_name)

    if is_gemini or is_claude:
        return _create_vertex_model(
            model_name, temperature, max_output_tokens, thinking_budget
        )

    return _create_vllm_model(model_name, temperature, max_output_tokens)


def _create_vertex_model(
    model_name: str,
    temperature: float,
    max_output_tokens: int,
    thinking_budget: int | None = None,
) -> BaseChatModel:
    """Create a Vertex AI model (Gemini or Claude)."""
    is_claude = is_claude_model(model_name)
    model_type = "Claude" if is_claude else "Gemini"

    try:
        credentials, project = get_service_account_credentials()

        logger.info(
            f"Creating {model_type} model via Vertex AI",
            model=model_name,
            project=project,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        if is_claude:
            return ChatAnthropicVertex(
                model=model_name,
                project=project,
                credentials=credentials,
                max_tokens=max_output_tokens,
                max_retries=2,
                streaming=True,
            )
        else:
            kwargs: dict = {
                "model": model_name,
                "temperature": temperature,
                "credentials": credentials,
                "project": project,
                "max_output_tokens": max_output_tokens,
                "max_retries": 2,
                "streaming": True,
                "safety_settings": safety_settings,
            }

            budget = _thinking_budget() if thinking_budget is None else thinking_budget
            if budget is not None:
                kwargs["thinking_budget"] = budget

            return ChatGoogleGenerativeAI(**kwargs)

    except (ValueError, LLMError):
        raise
    except Exception as e:
        logger.error(
            f"Failed to create {model_type} model '{model_name}'",
            error_type=type(e).__name__,
            model=model_name,
            error_message=str(e),
            exc_info=True,
        )
        raise LLMError(
            f"Failed to create {model_type} model '{model_name}': {e}"
        ) from e


def _create_vllm_model(
    model_name: str,
    temperature: float,
    max_output_tokens: int,
) -> BaseChatModel:
    """Create a model via vLLM / OpenAI-compatible endpoint."""
    if not settings.VLLM_BASE_URL:
        raise ValueError(
            f"Model '{model_name}' is not a Vertex AI model name "
            f"(those start with {', '.join(settings.vertex_model_prefixes)}). "
            f"Set VLLM_BASE_URL to serve it from an OpenAI-compatible endpoint."
        )

    try:
        from langchain_openai import ChatOpenAI

        logger.info(
            "Creating model via vLLM/OpenAI-compatible endpoint",
            model=model_name,
            base_url=settings.VLLM_BASE_URL,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        return ChatOpenAI(
            model=model_name,
            base_url=settings.VLLM_BASE_URL,
            api_key=SecretStr(settings.VLLM_API_KEY),
            temperature=temperature,
            max_completion_tokens=max_output_tokens,
            max_retries=2,
            streaming=True,
        )

    except ImportError:
        raise LLMError(
            "langchain-openai is required for vLLM support. "
            "Add 'langchain-openai' to your dependencies."
        )
    except Exception as e:
        logger.error(
            f"Failed to create vLLM model '{model_name}'",
            error_type=type(e).__name__,
            model=model_name,
            base_url=settings.VLLM_BASE_URL,
            error_message=str(e),
            exc_info=True,
        )
        raise LLMError(f"Failed to create vLLM model '{model_name}': {e}") from e
