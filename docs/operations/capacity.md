# Capacity

What this deployment can serve, and what decides it. The
connection-pool arithmetic is in [scalability.md](scalability.md);
this file is the two things that one does not cover — the
**provider quota** (SCALE-10) and the **sandbox pool**
(SCALE-13).

Every number here is either measured against the Kind cluster
or named as a deployment input. Where a number is an input
this file says so rather than inventing one, because a
capacity plan with a made-up quota in it is worse than no
plan: somebody will size against it.

## The provider is the ceiling, not the harness

NFR-SCALE fixes four meanings of "an interaction" and only
tier A is a flat target. Tier D — a model-backed turn — is
**provider-bound**, and SCALE-10 asks for the arithmetic
rather than a number.

### What one turn costs, measured

Taken from the `prompt_size` log line on this cluster, on a
turn whose user message is eight characters:

| | tokens |
|---|---|
| system prompt | 4,609 |
| tool schemas | 2,162 |
| the user's message | 2 |
| **input, trivial turn** | **6,773** |
| output, `max_output_tokens` ceiling | 8,192 |

A real turn is larger on both sides: the input grows with the
conversation and with any attached document, and a turn that
calls tools pays the input again on each model call. The
`model_call_limit.run_limit` in `agent.yaml` is 250, so a
single run's worst case is 250 model calls.

### The arithmetic

For a target of **R runs per second** at **I input tokens** and
**O output tokens** per model call, with **C** model calls per
run:

```
input  tokens/min = R × C × I × 60
output tokens/min = R × C × O × 60
```

At the trivial-turn numbers above, one model call per run and
a conservative 500 output tokens:

| R (runs/s) | input tokens/min | output tokens/min |
|---|---|---|
| 1 | 406,380 | 30,000 |
| 10 | 4,063,800 | 300,000 |
| 100 | 40,638,000 | 3,000,000 |
| 1,000 | 406,380,000 | 30,000,000 |

**This is the point of the table.** Tier D's headline figure of
1,000 runs/s needs 30 million output tokens a minute. No
deployment in this estate holds that quota, so the honest
target for tier D is *whatever the quota allows*, and the
harness's job is to not be the thing that runs out first.

### What the harness contributes

Measured on this cluster, so the two can be told apart:

* **63ms** of harness per run, from `Worker picked up run` to
  the model call (PERF-1).
* **24.6s** inside Vertex AI for the same trivial turn.

So at these latencies the harness is 0.3% of a turn. A tier-D
number that is missed is a provider number until the harness
side exceeds its PERF-1 budget.

### Filling this in for a deployment

Three inputs, none of which this template can know:

1. **The quota.** Tokens per minute, input and output
   separately, for the model named in
   `config/agent/runtime/agent.yaml`. From the provider's
   console, not from a guess.
2. **The expected mix.** Average input tokens and model calls
   per run, which the `prompt_size` log line reports for a
   real workload rather than for "say pong".
3. **The headroom.** What fraction of the quota this
   deployment may take, when others share it.

Then `R = quota_output_per_min / (C × O × 60)` and the pod
count follows from `MAX_CONCURRENT_RUNS` (40 today) and the
run duration.

## Per-pod admission

`MAX_CONCURRENT_RUNS` is **40** per pod, from the `tuning:`
block of `config/agent/deployment/values.yaml`. Sized against
the connection budget rather than CPU: a run is mostly idle
but holds a checkpointer connection for its whole life. The
arithmetic for that is in
[scalability.md](scalability.md).

Verified on the cluster: sixty concurrent `runs/wait` against
one pod gave forty 200s and twenty 503s carrying
`Retry-After: 5` (SCALE-4).

## Sandboxed execution — tier E

**There is no sandbox pool, because there is no sandbox.**

`sandbox_backend` exists as a declared feature flag (E21,
deployment scope, default `false`) and
`browser_automation_enabled` (E16) requires it. Neither has an
implementation: no pool, no queue, no admission path of its
own.

So SCALE-13 is not met, and recording a pool size here would
be recording a number for something that cannot enforce it.
What this file can fix is the part SCALE-13 asks for —
**the pool size is a capacity decision, written down, not a
default**. When tier E is built:

* the pool size belongs in this file with its reasoning, and
  in `values.yaml` so it is one number rather than two;
* a request beyond the pool waits with a stated position or is
  refused — it never starts a sandbox the cluster cannot
  place;
* the sizing is bounded by cluster capacity, not by request
  handling. Tier E is tens per second against tier A's
  thousand, three orders of magnitude apart, and an epic that
  assumes otherwise ships a feature that falls over at ten
  users.
