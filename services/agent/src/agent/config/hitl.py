"""Human-in-the-loop interrupt configuration builder."""

from __future__ import annotations

from typing import Any

from agent.src.agent.config.middleware import (
    ApprovalPolicy,
    HumanApprovalConfig,
)
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_MEMORY_PATH_PREFIX = settings.MEMORY_PATH_PREFIX

_SKILLS_PATH_PREFIX = settings.SKILLS_PATH_PREFIX

_READ_ONLY_FILE_TOOLS: frozenset[str] = frozenset({"read_file", "ls", "glob", "grep"})

_MEMORY_FILE_TOOLS: frozenset[str] = frozenset({"read_file", "write_file", "edit_file"})

_DEEPAGENTS_BUILTIN_TOOLS: frozenset[str] = frozenset(
    {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "write_todos",
        "task",
        "compact_conversation",
    }
)


def _tool_call_path(req: Any) -> str:
    """The path a filesystem tool call targets, or "" if it has none."""
    args = req.tool_call.get("args", {}) or {}
    return args.get("file_path") or args.get("path") or ""


def _is_non_memory_path(req: Any) -> bool:
    """Return True (interrupt) unless the file path is under /memories/."""
    return not _tool_call_path(req).startswith(_MEMORY_PATH_PREFIX)


def _is_non_exempt_path(req: Any) -> bool:
    """Return True (interrupt) unless the path is memory or a skill."""
    path = _tool_call_path(req)
    if path.startswith(_MEMORY_PATH_PREFIX):
        return False
    return not path.startswith(_SKILLS_PATH_PREFIX)


def _is_non_skill_read(req: Any) -> bool:
    """Return True (interrupt) unless the path is a skill."""
    return not _tool_call_path(req).startswith(_SKILLS_PATH_PREFIX)


def resolve_policy(
    tool_name: str,
    config: HumanApprovalConfig,
    *,
    effects: str = "live",
) -> ApprovalPolicy:
    """Return the policy governing one tool. First match wins, in order."""
    from agent.src.security.policy import ConfigPolicySource
    from agent.src.security.resolver import ToolCall

    return ConfigPolicySource(config, effects=effects).policy_for(
        ToolCall(name=tool_name)
    )


def _approval_description(tool_name: str, policy: ApprovalPolicy) -> str:
    """One line a human can act on, prefixed with severity."""
    severity = {"high": "[HIGH RISK] ", "medium": "", "low": "[low risk] "}[policy.risk]
    if policy.reason.startswith("No matching policy"):
        reason = "No approval policy covers this tool; approval required by default."
    else:
        reason = policy.reason or "No rationale configured for this tool."
    return f"{severity}{tool_name}: {reason}"


def describe_policies(
    tool_names: set[str],
    config: HumanApprovalConfig,
    *,
    effects: str = "live",
) -> dict[str, dict[str, Any]]:
    """Resolved decision, risk and rationale per tool."""
    return {
        name: {
            "decision": (p := resolve_policy(name, config, effects=effects)).decision,
            "risk": p.risk,
            "reason": p.reason,
        }
        for name in sorted(tool_names)
    }


def denied_tool_names(
    config: HumanApprovalConfig, tools: list[Any], *, effects: str = "live"
) -> frozenset[str]:
    """Tools the policy refuses outright."""
    if not config.enabled:
        return frozenset()

    names = {t.name for t in tools} | _DEEPAGENTS_BUILTIN_TOOLS
    return frozenset(
        name
        for name in names
        if resolve_policy(name, config, effects=effects).decision == "deny"
    )


def build_interrupt_on(
    config: HumanApprovalConfig,
    tools: list[Any],
    *,
    effects: str = "live",
) -> dict[str, Any]:
    """Build the ``interrupt_on`` dict for ``create_deep_agent()``."""
    if not config.enabled or config.mode == "none":
        logger.debug("HITL disabled (enabled=%s, mode=%s)", config.enabled, config.mode)
        return {}

    exclude = set(config.exclude)

    explicit_names = {t.name for t in tools}

    all_names = explicit_names | _DEEPAGENTS_BUILTIN_TOOLS

    interrupt_on: dict[str, Any] = {}
    denied: list[str] = []
    for name in all_names:
        decision = resolve_policy(name, config, effects=effects).decision
        if decision == "allow":
            continue
        if decision == "deny":
            denied.append(name)
            continue
        if name in _MEMORY_FILE_TOOLS and name in _READ_ONLY_FILE_TOOLS:
            predicate = _is_non_exempt_path
        elif name in _MEMORY_FILE_TOOLS:
            predicate = _is_non_memory_path
        elif name in _READ_ONLY_FILE_TOOLS:
            predicate = _is_non_skill_read
        else:
            predicate = None

        policy = resolve_policy(name, config, effects=effects)
        entry: dict[str, Any] = {
            "allowed_decisions": ["approve", "edit", "reject", "respond"],
            "description": _approval_description(name, policy),
        }
        if predicate is not None:
            entry["when"] = predicate
        interrupt_on[name] = entry

    if denied:
        logger.warning("Tools denied by approval policy: %s", sorted(denied))

    if interrupt_on:
        excluded = (explicit_names | _DEEPAGENTS_BUILTIN_TOOLS) - set(interrupt_on)
        memory_auto = sorted(_MEMORY_FILE_TOOLS - exclude)
        logger.info(
            "HITL enabled: %d tool(s) will require approval%s%s",
            len(interrupt_on),
            f" ({len(excluded)} excluded: {sorted(excluded)})" if excluded else "",
            f" (memory-only auto-approve: {memory_auto})" if memory_auto else "",
        )
    else:
        logger.debug(
            "HITL enabled but all tools excluded (explicit=%d, builtins=%d, exclude=%s)",
            len(explicit_names),
            len(_DEEPAGENTS_BUILTIN_TOOLS),
            exclude,
        )

    return interrupt_on
