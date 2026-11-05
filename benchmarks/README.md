# Benchmarks

Public agent benchmarks, run against this harness.

Different from two neighbours it is easy to confuse:

| | measures |
|---|---|
| `benchmarks/` | this agent against **somebody else's** published suite |
| `scripts/bench/` | one configuration against another, on suites we vendor |
| `test/load/` | capacity — how many users, how fast |

## What is here

| | |
|---|---|
| [`appworld/`](./appworld) | 9 apps, 457 APIs, 732 tasks. REPL protocol, state-based scoring. **Working.** |

## What is not, and why

**WebArena** needs a capability this agent does not have. Its
agents drive a browser, and `browser_automation_enabled` is a flag
in `config/agent/runtime/features.yaml` that **no code reads** —
`make capability-gates` lists it as "E16, browser automation, is
not built", and it additionally `requires: sandbox_backend`, which
is also unbuilt. Self-hosting is six sites via their
`environment_docker` tree, which is the smaller half of the
problem.

So WebArena is not a adapter away; it is a browser tool, an
observation encoder and an action space away. Worth doing on
purpose, not as a benchmark side-quest.

## Before quoting a number anywhere

`docs/development/bench.md` makes the argument and it applies here too:

> An absolute score against a public leaderboard flatters or
> insults depending on how close the suite is to what this agent
> is for.

The honest use of these is a **delta** — the same suite, the same
split, two configurations of this harness, and which did better.
An absolute figure needs the protocol to match theirs exactly, and
the caveats belong next to the number rather than in a footnote.

Each suite's directory says what it does and does not match.

## Isolation

Each suite gets its own virtualenv under `benchmarks/.venv`.
AppWorld alone pulls a large dependency tree, and resolving it
into the agent's environment would change what the agent runs —
which is the one thing a measurement must not do.

```sh
uv venv benchmarks/.venv --python 3.12
uv pip install --python benchmarks/.venv/bin/python appworld
```
