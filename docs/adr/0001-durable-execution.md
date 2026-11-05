# 1. Durable execution: Temporal, around Aegra

- **Status:** Accepted (D-15, 2026-10-26)
- **Epic:** E18
- **Flag:** `event_service_enabled` — `config/agent/runtime/features.yaml`, deployment scope, default **false**

## The problem

Work disappears when a pod does. Aegra checkpoints a turn, so a run
interrupted mid-turn is picked up by `resume_interrupted_runs` at
startup. Nothing recovers the work *between* turns: a scheduled job
three steps into five, an inbound event handed to a run that then
died, a long task somebody started and walked away from. Those are
not rare cases — they are the whole of unattended operation, which is
what scheduling and long-running tasks are for.

## The decision

**Temporal is the durable execution engine, and the boundary is the
Agent Protocol.** Multi-step, scheduled and event-driven work becomes
a Temporal workflow whose activities are HTTP calls against this
agent's own public API — `POST /threads`, `POST /threads/{id}/runs`,
`/runs/{id}/join`, `/runs/{id}/cancel`.

**The agent turn stays Aegra-checkpointed.** A pod loss mid-turn is
recovered the way it is today. A pod loss between turns, or part-way
through a multi-step job, is recovered by Temporal.

### The shapes that were rejected, and why

| Shape | What becomes a workflow | Verdict |
|---|---|---|
| **A. Temporal around Aegra** | Work that coordinates turns; each activity is an Agent Protocol call | **Chosen.** Aegra keeps runs, checkpoints and the queue it already owns. |
| B. Temporal inside the turn | Each tool call an activity, the turn a workflow | Rejected. Better semantics, but it replaces Aegra's run loop — a fork, which D-4 forbids. |
| C. Temporal for inbound events only | The event, not the work it triggers | Rejected as too narrow. A durable event handed to a run that dies is a durable record of a lost answer. |

## What this obliges, stated plainly

**Workflow code is deterministic.** No model call, no clock read, no
random value, no HTTP call in workflow code — all of it goes in an
activity. This is the constraint people discover late, and it is the
reason the boundary sits at the Agent Protocol rather than inside the
graph: a graph node cannot be made deterministic without rewriting it.

**Payloads go by reference.** A workflow carries thread and run
identifiers, never message content. Temporal's payload limits are
small next to a conversation, and history grows with every event; the
content stays in Postgres where it already lives.

**History is readable by whoever operates the cluster.** So whatever
does cross — identifiers, tool names, channel metadata — passes
through an encrypting data converter. The scrubbing posture applies to
workflow history too, and assuming otherwise is how it leaks.

**One scheduler, not two.** Aegra cron and Temporal schedules both
running is the worst outcome available. Either cron migrates with a
rollback written first, or an ADR says Aegra cron stays and Temporal
never schedules. No quiet coexistence.

**The worker is a role on the one image.** `harness worker` beside
`harness agent` and `harness ui` — same image, same tag, its own
Deployment, so worker and agent versions cannot diverge.

**It is a real operational dependency.** A Temporal server, its own
database and a UI, in compose, Kind, preprod and prod.

## Optional, and that is load-bearing

A deployment that does not want Temporal must still run the harness
unchanged. With `event_service_enabled` off: **no worker runs, no
connection is attempted, and nothing in the request path differs**
(INV-8). The flag is deployment-scoped — a person cannot turn on an
operational dependency for themselves.

## How to tell whether code may be a workflow

Ask whether it would produce the same result if replayed from history
with no side effects. If it reads a clock, calls a model, touches the
network or generates a uuid, it is an activity. If it only decides
what to do next from values it was given, it may be a workflow.

## Consequences accepted

- A Temporal cluster in four environments, rendered from
  `values.yaml` like everything else (CI-10).
- The dev loop must start it without making the inner loop slower
  (E27), and it stays off the per-interaction critical path
  (SCALE-9): one interaction is tens of state transitions, an order
  of magnitude past a single cluster's published range.
- Failure drills belong in the nightly tier (E18-T12): kill the
  worker mid-workflow, kill Temporal, kill the agent — each resumes
  or fails loudly, never silently drops work.

## Open

**D-11 — who owns inbound ingress** is narrowed, not answered.
Temporal settles durability; it does not settle whether the gateway
hands events to Temporal or this harness receives them directly.
E18-T2 onward can proceed either way; E18-T8 cannot.
