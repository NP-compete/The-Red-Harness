"""An approval belongs to the person who triggered the run (E33-T4)."""

from __future__ import annotations

from agent.src.spaces.store import ActiveRun
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


class ApprovalNotYours(PermissionError):
    """Someone other than the run's owner tried to answer for it."""

    def __init__(self, *, actor: str, owner: str | None) -> None:
        """Record who tried to approve, and whose action it is."""
        self.actor, self.owner = actor, owner
        super().__init__(
            "this pending action belongs to "
            + (owner if owner else "somebody who cannot be identified")
            + ", and only they can approve it. The agent would act with "
            "their access, not yours."
        )


def may_answer(run: ActiveRun | None, *, actor: str) -> bool:
    """Only the person whose run it is."""
    if run is None:
        return False
    return bool(run.triggered_by) and actor == run.triggered_by


def check_may_answer(run: ActiveRun | None, *, actor: str, space_id: str) -> None:
    """Raise unless this actor owns the pending action."""
    if may_answer(run, actor=actor):
        return
    owner = run.triggered_by if run else None
    logger.warning(
        "approval refused: %s tried to answer a run owned by %s in space %s",
        actor,
        owner or "nobody",
        space_id,
    )
    raise ApprovalNotYours(actor=actor, owner=owner)
