"""Running one benchmark task against this agent."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)


class Transport(Protocol):
    """Makes requests to the agent on the benchmark's behalf."""

    def post(
        self, path: str, body: dict | None = None, timeout: float | None = None
    ) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        ...

    def delete(self, path: str) -> tuple[int, Any]:
        """DELETE `path` and return the status and decoded body."""
        ...


@dataclass(frozen=True)
class Attempt:
    """What one task produced. Deliberately not a score."""

    text: str
    cost: float = 0.0
    error: str = ""


@dataclass
class AgentExecutor:
    """Runs one benchmark task against a live agent."""

    transport: Transport
    assistant_id: str = "agent"

    def run(
        self,
        *,
        cwd: Path,
        mission: str,
        system: str = "",
        wall: int = 900,
    ) -> Attempt:
        """One task, start to finish, leaving nothing behind."""
        if wall <= 0:
            raise ValueError(f"a wall of {wall}s gives no task time to answer")

        _write_mission(cwd, mission=mission, system=system)

        thread_id = self._conversation()
        if thread_id is None:
            return Attempt(text="", error="the agent would not start a conversation")

        try:
            found = self._ask(thread_id, mission=mission, wall=wall)
        finally:
            self._forget(thread_id)

        if found.text:
            _write_answer(cwd, found.text)
        return found

    def _conversation(self) -> str | None:
        """Open a thread and return its id, or `None` if that fails."""
        try:
            status, body = self.transport.post("/threads", {})
        except Exception:
            return None
        if status not in (200, 201) or not isinstance(body, dict):
            return None
        return str(body.get("thread_id") or "") or None

    def _ask(self, thread_id: str, *, mission: str, wall: int) -> Attempt:
        """Put one mission to the agent and return what came back."""
        from agent.cli.outcome import NoAnswer, RunFailedInBody, outcome_of

        try:
            status, state = self.transport.post(
                f"/threads/{thread_id}/runs/wait",
                {
                    "assistant_id": self.assistant_id,
                    "input": {"messages": [{"role": "user", "content": mission}]},
                },
                timeout=wall,
            )
        except TimeoutError:
            self._cancel(thread_id)
            return Attempt(text="", error=f"ran out of time after {wall}s")
        except Exception as error:
            return Attempt(text="", error=f"the agent could not be reached: {error}")

        if status not in (200, 201):
            return Attempt(text="", error=f"the run was refused ({status})")

        try:
            answered = outcome_of(state, thread_id=thread_id)
        except RunFailedInBody as threw:
            return Attempt(text="", error=str(threw))
        except NoAnswer:
            return Attempt(text="", error="the agent answered with nothing")

        if answered.paused is not None:
            waiting = ", ".join(
                str(entry.get("action") or "")
                for entry in answered.paused.get("awaiting") or []
            )
            return Attempt(
                text="",
                error=f"the run stopped for a decision on: {waiting or 'an action'}",
            )

        return Attempt(text=answered.text)

    def _cancel(self, thread_id: str) -> None:
        """Cancel whatever is running on `thread_id`, ignoring failures."""
        try:
            self.transport.post(f"/threads/{thread_id}/runs/cancel", {})
        except Exception:
            pass

    def _forget(self, thread_id: str) -> None:
        """Delete `thread_id`, ignoring failures."""
        try:
            self.transport.delete(f"/threads/{thread_id}")
        except Exception:
            pass


def _write_mission(cwd: Path, *, mission: str, system: str) -> None:
    """Write the mission, with the system prompt above it, into `cwd`."""
    cwd.mkdir(parents=True, exist_ok=True)
    above = f"{system}\n\n---\n\n" if system else ""
    (cwd / "MISSION.md").write_text(above + mission, encoding="utf-8")


def _write_answer(cwd: Path, text: str) -> None:
    """Where the runner looks first."""
    out = cwd / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "answer.md").write_text(text, encoding="utf-8")


@dataclass
class HttpTransport:
    """The run API over HTTP, which is how a suite reaches it."""

    base_url: str

    def post(
        self, path: str, body: dict | None = None, timeout: float | None = None
    ) -> tuple[int, Any]:
        """POST `body` to `path` and return the status and decoded body."""
        import httpx

        try:
            found = httpx.post(
                f"{self.base_url}{path}", json=body or {}, timeout=timeout
            )
        except httpx.TimeoutException as expired:
            raise TimeoutError(str(expired)) from None
        return found.status_code, _body_of(found)

    def delete(self, path: str) -> tuple[int, Any]:
        """DELETE `path` and return the status and decoded body."""
        import httpx

        found = httpx.delete(f"{self.base_url}{path}", timeout=30)
        return found.status_code, _body_of(found)


def _body_of(response: Any) -> Any:
    """The decoded body of `response`, or an empty dict."""
    try:
        return response.json()
    except Exception:
        return {}
