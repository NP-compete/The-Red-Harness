"""A job that outlives every process running it (E18, D-15)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import activity, workflow

TASK_QUEUE = "harness-durable"


@dataclass
class Step:
    """One unit of work, and how long to wait before the next one."""

    instruction: str
    wait_seconds: int = 0


@dataclass
class JobRequest:
    """A multi-step job, by reference."""

    owner: str
    thread_id: str
    steps: list[Step] = field(default_factory=list)


@dataclass
class StepResult:
    """What one step of a durable job produced."""

    run_id: str
    status: str


@dataclass
class JobResult:
    """What a durable job produced, step by step."""

    thread_id: str
    completed: int
    results: list[StepResult] = field(default_factory=list)


@dataclass
class StepRequest:
    """What an activity needs to run one step."""

    owner: str
    thread_id: str
    instruction: str


class AgentActivities:
    """The side effects, kept out of workflow code."""

    def __init__(self, base_url: str) -> None:
        """Bind the activities to the agent at `base_url`."""
        self._base_url = base_url.rstrip("/")

    @activity.defn(name="run_step")
    async def run_step(self, request: StepRequest) -> StepResult:
        """Start one run and wait for it to finish."""
        import httpx

        headers = {"X-User-Id": request.owner}
        async with httpx.AsyncClient(timeout=600) as client:
            started = await client.post(
                f"{self._base_url}/threads/{request.thread_id}/runs",
                json={
                    "assistant_id": "agent",
                    "input": {
                        "messages": [{"role": "human", "content": request.instruction}]
                    },
                },
                headers=headers,
            )
            started.raise_for_status()
            run_id = started.json()["run_id"]

            joined = await client.get(
                f"{self._base_url}/threads/{request.thread_id}/runs/{run_id}/join",
                headers=headers,
            )
            status = "unknown"
            if joined.status_code < 400:
                settled = await client.get(
                    f"{self._base_url}/threads/{request.thread_id}/runs/{run_id}",
                    headers=headers,
                )
                if settled.status_code < 400:
                    status = str(settled.json().get("status") or "unknown")
        return StepResult(run_id=run_id, status=status)


@workflow.defn(name="DurableJob")
class DurableJob:
    """Steps, with waiting between them, surviving everything."""

    def __init__(self) -> None:
        """Start with no steps finished."""
        self._done = 0

    @workflow.query
    def progress(self) -> int:
        """How many steps are finished, askable while it waits."""
        return self._done

    @workflow.run
    async def run(self, request: JobRequest) -> JobResult:
        """Run each step in turn and collect the results."""
        results: list[StepResult] = []
        for step in request.steps:
            result = await workflow.execute_activity(
                "run_step",
                StepRequest(
                    owner=request.owner,
                    thread_id=request.thread_id,
                    instruction=step.instruction,
                ),
                start_to_close_timeout=timedelta(hours=1),
                heartbeat_timeout=timedelta(minutes=5),
            )
            results.append(result)
            self._done += 1

            if step.wait_seconds:
                await workflow.sleep(timedelta(seconds=step.wait_seconds))

        return JobResult(
            thread_id=request.thread_id,
            completed=self._done,
            results=results,
        )
