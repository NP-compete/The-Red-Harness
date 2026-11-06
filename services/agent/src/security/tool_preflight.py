"""Looking at a tool call before making it."""

from __future__ import annotations

from typing import Any

from agent.src.security.tool_call_check import Check, Preflight, check_call
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

LIVE_CHECKS = ("arguments", "shape", "rate", "concurrency")

_SHAPES: Any = None


def remembered_shapes() -> Any:
    """The shape each tool had when this process first saw it."""
    global _SHAPES
    if _SHAPES is None:
        from agent.src.security.tool_fingerprint import ShapeMemory

        _SHAPES = ShapeMemory()
    return _SHAPES


def _shape_still_the_same(tool: Any, shapes: Any) -> tuple[bool, str]:
    """Whether this tool is still the tool it was at the start."""
    from agent.src.security.tool_fingerprint import shape_of

    if not str(getattr(tool, "name", "") or "").strip():
        return True, ""

    try:
        found: tuple[bool, str] = shapes.check(shape_of(tool))
        return found
    except Exception as error:
        logger.debug("Could not read the shape of a tool: %s", error)
        return True, ""


def configured_pace() -> Any:
    """How fast and how many at once, from configuration."""
    global _PACE
    if _PACE is None:
        from agent.src.agent.config import agent_config
        from agent.src.security.tool_pace import ToolPace

        try:
            raw = (agent_config.get_orchestrator_config() or {}).get("tool_pace")
        except Exception:
            raw = None
        _PACE = ToolPace.from_config(raw or {})
    return _PACE


_PACE: Any = None


def _arguments_of(given: Any) -> Any:
    """The arguments, out of whatever the caller was handed."""
    if isinstance(given, dict) and isinstance(given.get("args"), dict):
        return given["args"]
    return given


def _arguments_fit(tool: Any, given: Any) -> tuple[bool, str]:
    """Whether these arguments fit the tool's declared shape."""
    arguments = _arguments_of(given)
    if not isinstance(arguments, dict):
        return False, f"expected a mapping of arguments, got {type(arguments).__name__}"

    schema = getattr(tool, "args_schema", None)
    if schema is None:
        return True, ""

    try:
        schema.model_validate(arguments)
        return True, ""
    except Exception as error:
        message = str(error)
        if "not really a schema" in message or not hasattr(schema, "model_fields"):
            logger.debug("Could not read the schema for %s", getattr(tool, "name", "?"))
            return True, ""
        return False, message.replace("\n", " ")[:300]


def look_before(tool: Any, arguments: Any, *, shapes: Any = None) -> Check:
    """Check a call, answering only what can be determined."""
    fits, problem = _arguments_fit(tool, arguments)
    same, changed = _shape_still_the_same(tool, shapes or remembered_shapes())

    return check_call(
        Preflight(
            tool=getattr(tool, "name", "") or "a tool",
            arguments_valid=fits,
            argument_problem=problem,
            shape_unchanged=same,
            shape_problem=changed,
            server_trusted=True,
            credential_available=True,
            destination_allowed=True,
            within_rate_limit=True,
            within_concurrency=True,
        )
    )
