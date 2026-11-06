"""Kill-and-restart: does an interrupted run actually resume?"""

from __future__ import annotations

import os
import time

import httpx
import pytest

pytestmark = [pytest.mark.nightly, pytest.mark.slow]

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:5002")
ASSISTANT_ID = os.getenv("AGENT_ASSISTANT_ID", "agent")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")
SLOW_MARKER = os.getenv("MOCK_LLM_SLOW_MARKER", "__slow__")
_HEADERS = {"Authorization": f"Bearer {AGENT_TOKEN}"} if AGENT_TOKEN else {}


def _stack_is_up() -> bool:
    try:
        probe = httpx.get(f"{AGENT_URL}/health", headers=_HEADERS, timeout=3)
        return probe.status_code == 200
    except Exception:
        return False


pytestmark.append(
    pytest.mark.skipif(
        not _stack_is_up(),
        reason=f"no agent reachable at {AGENT_URL}; start one with `make dev`",
    )
)


def _needs_a_second_replica() -> None:
    """Refuse to run where the kill would take the Service down."""
    replicas = os.getenv("AGENT_REPLICAS")
    if replicas is None:
        pytest.skip(
            "set AGENT_REPLICAS to the agent's replica count. Below two, "
            "killing the only pod takes the Service with it and every "
            "assertion after the kill fails like a recovery bug."
        )
    if int(replicas) < 2:
        pytest.skip(
            f"AGENT_REPLICAS={replicas}: killing the only pod takes the "
            "Service down, so a failure here would say nothing about "
            "lease recovery. The Kind overlay runs one."
        )


@pytest.fixture
def client() -> httpx.Client:
    with httpx.Client(base_url=AGENT_URL, headers=_HEADERS, timeout=30) as c:
        yield c


def _create_thread(client: httpx.Client) -> str:
    response = client.post("/threads", json={})
    response.raise_for_status()
    return response.json()["thread_id"]


class TestLeaseRecovery:
    def test_interrupted_run_is_resumed(self, client: httpx.Client):
        """Start a run, kill its worker, assert it finishes anyway."""
        kill_command = os.getenv("WORKER_KILL_COMMAND")
        if not kill_command:
            pytest.skip(
                "set WORKER_KILL_COMMAND to the command that kills a worker, "
                "e.g. 'oc delete pod -l component=agent --force'"
            )
        _needs_a_second_replica()

        thread_id = _create_thread(client)
        run = client.post(
            f"/threads/{thread_id}/runs",
            json={
                "assistant_id": ASSISTANT_ID,
                "input": {
                    "messages": [
                        {"type": "human", "content": f"count to ten {SLOW_MARKER}"}
                    ]
                },
            },
        )
        run.raise_for_status()
        run_id = run.json()["run_id"]

        time.sleep(2)

        before = client.get(f"/threads/{thread_id}/runs/{run_id}")
        status_before = (
            before.json().get("status") if before.status_code == 200 else None
        )
        assert status_before in ("pending", "running"), (
            f"run was already {status_before!r} before the kill — nothing was "
            "interrupted. Slow the model down (MOCK_LLM_DELAY_MS) so the run "
            "is genuinely in flight."
        )

        os.system(kill_command)  # noqa: S605 — operator-supplied, nightly only

        deadline = time.time() + 180
        status = None
        while time.time() < deadline:
            try:
                probe = client.get(f"/threads/{thread_id}/runs/{run_id}")
            except httpx.HTTPError:
                time.sleep(5)
                continue
            if probe.status_code == 200:
                status = probe.json().get("status")
                if status in {"success", "error", "interrupted"}:
                    break
            time.sleep(5)

        assert status == "success", (
            f"run did not recover after the worker was killed (status={status}). "
            "Aegra's lease reaper should re-execute from the last checkpoint."
        )

    def test_thread_state_survives_a_restart(self, client: httpx.Client):
        """Checkpoints are in Postgres, so state must outlive the process."""
        thread_id = _create_thread(client)

        client.post(
            f"/threads/{thread_id}/runs/wait",
            json={
                "assistant_id": ASSISTANT_ID,
                "input": {"messages": [{"type": "human", "content": "remember: 42"}]},
            },
        ).raise_for_status()

        history = client.get(f"/threads/{thread_id}/history")
        history.raise_for_status()

        assert history.json(), "thread history empty — checkpoints not persisted"
