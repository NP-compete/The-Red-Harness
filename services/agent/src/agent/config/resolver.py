"""Skill and tool resolution utilities."""

from pathlib import Path
from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)


def resolve_skill_paths(
    skill_names: list[str],
    available_skills: dict[str, Path],
    agent_name: str = "agent",
) -> list[str]:
    """Resolve skill names to skill directory paths using cached skill index."""
    skill_paths: list[str] = []
    missing: list[str] = []

    for skill_name in skill_names:
        if skill_name in available_skills:
            skill_path = available_skills[skill_name]
            skill_paths.append(str(skill_path))
            logger.debug(f"Agent '{agent_name}' resolved skill: {skill_name}")
        else:
            missing.append(skill_name)

    if missing:
        logger.warning(f"Agent '{agent_name}' references unknown skills: {missing}")

    return skill_paths


def to_virtual_skill_sources(skill_paths: list[str]) -> list[str]:
    """Virtual *source* directories to scan for the given skills."""
    sources: set[str] = set()
    for p in skill_paths:
        parent_name = Path(p).parent.name
        if parent_name != "skills":
            logger.warning(
                "Skill path '%s' is not directly under a 'skills/' directory "
                "— scanning '/skills/' anyway; nested skill directories are "
                "not supported",
                p,
            )
        sources.add("/skills/")
    return sorted(sources)


def resolve_tools(
    tool_names: list[str],
    available_tools: list[Any],
    agent_name: str = "agent",
) -> list[Any]:
    """Resolve tool names to actual tool objects."""
    tool_by_name = {t.name: t for t in available_tools}
    resolved = [tool_by_name[n] for n in tool_names if n in tool_by_name]
    missing = [n for n in tool_names if n not in tool_by_name]

    if missing:
        logger.warning(f"Agent '{agent_name}' references unknown tools: {missing}")

    return resolved
