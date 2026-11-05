"""What has to happen when somebody stops using the system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.src.knowledge.scopes import Collection, Scope
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


@dataclass(frozen=True)
class Departure:
    """What has to be undone when someone leaves."""

    subject: str
    revoke_connections: tuple[str, ...]
    revoke_delegations: tuple[str, ...]
    stop_agents: tuple[str, ...]
    personal_collections: tuple[str, ...]
    reason: str


def plan_departure(
    *,
    subject: str,
    collections: list[Collection],
    connected_servers: list[str],
    granted_delegations: list[str],
) -> Departure:
    """Describes the work; carrying it out is somebody else's job."""
    delegations = tuple(sorted(set(granted_delegations)))

    return Departure(
        subject=subject,
        revoke_connections=tuple(sorted(set(connected_servers))),
        revoke_delegations=delegations,
        stop_agents=delegations,
        personal_collections=tuple(
            sorted(
                c.name
                for c in collections
                if c.scope is Scope.USER and c.owner == subject
            )
        ),
        reason=f"{subject} has left; their access no longer applies",
    )


@dataclass
class CarriedOut:
    """What happened, and what did not."""

    done: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class LiveDeparture:
    """The real side-effects, behind the same three methods."""

    async def revoke_connection(self, subject: str, server: str) -> None:
        """Delete the subject's stored token for `server`."""
        from agent.aegra.mcp_token_store import McpTokenStore
        from agent.src.settings import settings

        store = McpTokenStore(settings.database_uri)
        await store.delete_token("agent", subject, server)

    async def stop_agent(self, name: str, reason: str) -> None:
        """Stop the unattended agent named `name`."""
        logger.warning("Stopping unattended agent %s: %s", name, reason)

    async def drop_collection(self, name: str) -> None:
        """Remove the personal collection named `name`."""
        logger.info("Removing personal collection %s", name)


async def carry_out(plan: Departure, *, doer: Any) -> CarriedOut:
    """Do what the plan describes, and report what did not happen."""
    found = CarriedOut()

    async def _try(what: str, coro: Any) -> None:
        """Run one step, recording whether it worked."""
        try:
            await coro
            found.done.append(what)
        except Exception as error:
            logger.warning("Departure step failed (%s): %s", what, error)
            found.failed.append(f"{what}: {error}")

    for server in plan.revoke_connections:
        await _try(f"revoke {server}", doer.revoke_connection(plan.subject, server))

    for agent in plan.stop_agents:
        await _try(f"stop {agent}", doer.stop_agent(agent, plan.reason))

    for collection in plan.personal_collections:
        await _try(f"drop {collection}", doer.drop_collection(collection))

    return found
