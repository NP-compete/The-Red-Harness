"""The worker role: `harness worker` (E18-T3, E18-T11)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

FLAG = "event_service_enabled"

CONNECT_DEADLINE_SECONDS = 120.0
MAX_BACKOFF_SECONDS = 15.0


def temporal_address() -> str:
    """Where the Temporal server is."""
    return os.environ.get("TEMPORAL_ADDRESS", "temporal:7233")


def temporal_namespace() -> str:
    """The Temporal namespace to run in."""
    return os.environ.get("TEMPORAL_NAMESPACE", "default")


def agent_base_url() -> str:
    """Where activities call the Agent Protocol."""
    return os.environ.get("AGENT_BASE_URL", "http://agent:5002")


def durable_execution_enabled() -> bool:
    """Whether this deployment asked for durable execution."""
    override = os.environ.get("EVENT_SERVICE_ENABLED")
    if override is not None:
        return override.strip().lower() in ("1", "true", "yes", "on")

    try:
        import yaml

        from agent.src.agent.config.features import from_config
        from agent.src.agent.config.paths import config_root

        registry_file = config_root() / "runtime" / "features.yaml"
        if not registry_file.is_file():
            return False
        declared = from_config(yaml.safe_load(registry_file.read_text()))
    except Exception:  # noqa: BLE001 — unreadable config is not "on"
        logger.warning("Could not read features.yaml; durable execution stays off")
        return False

    feature = declared.get(FLAG)
    return bool(getattr(feature, "default", False)) if feature else False


async def connect_with_retry(
    address: str,
    namespace: str,
    *,
    deadline_seconds: float = CONNECT_DEADLINE_SECONDS,
) -> Any:
    """Connect to Temporal, tolerating a server that is still starting."""
    from temporalio.client import Client

    loop = asyncio.get_running_loop()
    deadline = loop.time() + deadline_seconds
    delay = 1.0
    while True:
        try:
            return await Client.connect(address, namespace=namespace)
        except RuntimeError as exc:
            if loop.time() + delay >= deadline:
                raise
            logger.info("Temporal not ready yet (%s); retrying in %.0fs", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_BACKOFF_SECONDS)


async def run_worker() -> int:
    """Serve the durable task queue until stopped."""
    if not durable_execution_enabled():
        logger.warning(
            "Not starting: '%s' is off. Turn it on in "
            "config/agent/runtime/features.yaml (deployment scope) or set "
            "EVENT_SERVICE_ENABLED=true. No connection was attempted.",
            FLAG,
        )
        return 0

    from temporalio.worker import Worker

    from agent.src.workflows.durable import (
        TASK_QUEUE,
        AgentActivities,
        DurableJob,
    )

    address, namespace = temporal_address(), temporal_namespace()
    logger.info("Connecting to Temporal at %s (namespace %s)", address, namespace)
    client = await connect_with_retry(address, namespace)

    activities = AgentActivities(agent_base_url())
    logger.info("Worker serving '%s'; activities call %s", TASK_QUEUE, agent_base_url())

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[DurableJob],
        activities=[activities.run_step],
    ):
        await asyncio.Event().wait()
    return 0
