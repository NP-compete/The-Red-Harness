# Measuring a configuration

A feature table is an argument about surface. This is the other
kind of claim: the same suite, the same model, two configurations,
and a number that says which one did better.

The suites and their runners are somebody else's work, vendored.
What belongs here is an adapter, and this note is what you need to
write one without reading their source.

## What a runner expects from an executor

A runner hands over a **session**, not a request. Concretely:

| It gives you | |
|---|---|
| `cwd` | A directory it owns. Everything the task provides is in it. |
| `mission` | What to do, in prose. |
| `system` | Instructions that sit above the mission. May be empty. |
| `wall` | Seconds. After this it is entitled to give up on you. |

| It wants back | |
|---|---|
| `text` | The answer. |
| `cost` | What the attempt cost, in dollars. `0.0` if unknown. |
| `error` | Empty when it worked; a short reason when it did not. |

Three rules that are not obvious from the shape:

1. **The answer goes in two places.** `output/answer.md` under
   `cwd`, *and* returned as text. The runner prefers the file and
   falls back to the text, because an agent that writes a long
   answer to a file and summarises it in chat would otherwise be
   scored on the summary.
2. **An empty answer is a failure, not a score of zero.** Return
   it as `error`. A blank scored as wrong is indistinguishable
   from a wrong answer, and the two need different fixes.
3. **`error` is for the attempt, not the task.** An agent that
   correctly says "there is not enough information here" has
   succeeded at the attempt. A timeout has not.

## What one task hands over

The mission text and whatever files the suite put in `cwd`.
Nothing else — no task id, no metadata, no scoring hints. The
agent sees what a person would see.

## What a result looks like

Per task: an id, a domain, a status, and any errors. The suite
aggregates; the executor does not score itself and must not try.

## The shape of the adapter here

This agent speaks a run API rather than a CLI, so the shim is an
HTTP client:

```
POST /threads                      → a conversation
POST /threads/{id}/runs/wait       → the mission, and the answer
```

**One task is one conversation.** That is isolation for free: no
task can see another's history, and a task that poisons its own
context poisons only itself.

**The conversation is deleted when the task ends**, whether it
ended well or not. A failed run that leaves its thread behind is
how a long suite fills a database with the wreckage of the first
hour.

**A timeout cancels the run before giving up on it.** Walking
away from an HTTP request leaves the run going: it keeps spending
money, keeps a model busy, and lands in the next count of what
the suite cost.

## Prerequisites

Ask, rather than read a list:

```sh
make bench                  # names every unmet prerequisite, runs nothing
make bench BENCH=wbb
```

It reports all of them at once and exits non-zero if any is
unmet. A harness that fails on the first missing piece tells you
what crashed rather than what you need, and a clean checkout is
missing several:

| | |
|---|---|
| An agent at `AGENT_PORT` (5002) set to `dry_run` | see below |
| The suite's dataset | vendored as a *pointer*: `examples/harness2/dependencies/` holds `ASSETS.json` and `PINNED.md` and no data |
| A judge model that is not a mock | the suites score with a rubric judge, which is a model call |
| The suite runner | `scripts/bench/executor.py` is the half that plugs into `harness2`'s runner; the runner, with its substrates and rubric judge, is not vendored here |

**The model it reports is the one that will answer, not the one
in the configuration.** `/admin/config` says `gemini-3.8-flash`
while `MODEL_OVERRIDE=mock-model` sends every call to the stub on
:5004. A results row carrying the configured name would attribute
a stub's answers to a real model, in an append-only store, for
ever — so the override is asked first.

## The benchmark profile

Benchmarks need tools the product does not ship, so they get a
tree of their own at `config/bench/`, selected by `CONFIG_PATH`:

```sh
CONFIG_PATH=config/bench .venv/bin/aegra dev --port 5003
```

| | `config/agent` | `config/bench` |
|---|---|---|
| Name | Workpilot | Workpilot (measurement) |
| Remote servers | the ones you connected | none |
| Effects | whatever you deployed | `dry_run` |

The property worth testing is not that the measurement tree is
right. It is that the working tree is **untouched** by it, and a
test asserts that directly rather than trusting the directory
boundary — including that nothing under `config/bench/` names a
path back into `config/agent/`.

Before a run, check what you are pointed at:

```sh
make bench-check                 # exits non-zero if it is not safe
AGENT_PORT=5003 make bench-check
```

It refuses when `execution.effects` is anything but `dry_run`,
and also when the agent will not say — assuming `dry_run`
because a setting was renamed is how a suite ends up running
against production. The check is an allowlist for that reason.

## Reading the results

Append-only, one row per run, keyed by the configuration
fingerprint the graph already computes. That key is the point: a
score that cannot be traced back to exactly the configuration
that earned it is a number without a claim attached.

```sh
make bench-compare A=<fingerprint> B=<fingerprint>
```

**The delta is the number that matters.** An absolute score
against a public leaderboard flatters or insults depending on
how close the suite is to what this agent is for, and these
suites assume a generalist with broad tool access. Comparing a
configuration against another configuration removes that
question entirely.

When the comparison is against somebody else's system rather
than a previous self, it is still a delta — and the same honesty
applies. If the suite advantages a generalist, that belongs next
to the number, not in a footnote nobody reads.
