# The Red Harness

An agent you configure rather than fork. One image, several roles;
the behaviour lives in a config tree you can edit from the interface
or from the repository, and the two stay in step.

## Start here

| | |
|---|---|
| [The inner loop](guides/dev-loop.md) | run it on your machine, with the datastores in containers |
| [`harness`](reference/cli.md) | every command, generated from the parser |
| [Config reference](reference/config-reference.md) | every setting, generated from the models |

## Build an agent

| | |
|---|---|
| [Skills](guides/skills.md) | what a skill is and how one is loaded |
| [Two things called documents](guides/documents.md) | attachments and the corpus, which are not the same |
| [Document extraction](guides/extraction.md) | what comes out of a PDF, and what does not |
| [Tags and sharing](guides/tags-and-sharing.md) | who else sees a thread |
| [Being called by another system](guides/interop.md) | the agent as somebody else's dependency |

## Run it

| | |
|---|---|
| [Runbook](operations/runbook.md) | what to do when it is broken |
| [Service level objectives](operations/slo.md) | what it promises, and how that is measured |
| [Observability](operations/observability.md) | traces, metrics, and which questions they answer |
| [Capacity](operations/capacity.md) | what it needs to serve a given load |
| [Scaling to 1000 concurrent users](operations/scalability.md) | where it stops being one pod |
| [Postmortem template](operations/postmortem.md) | after it breaks |

## Trust it

| | |
|---|---|
| [Who may do what](security/authorization.md) | identity, policy, and the refusal codes |
| [Guardrails risk register](security/guardrails-risk-register.md) | what is guarded, and what is not |
| [The memory fence](security/memory.md) | why the agent's memory cannot instruct it |
| [Measuring a configuration](development/bench.md) | evaluating a change before shipping it |
| [Evaluation tables](development/eval-erd.md) | where eval results are stored |

## Change it safely

| | |
|---|---|
| [The pipeline](development/ci.md) | what a pull request runs |
| [Configuration compatibility](development/compatibility.md) | which config trees a new build still loads |
| [Built, tested, and reached by nothing](development/unreachable.md) | the modules nothing calls, and why they are kept |
| [Usage analytics](operations/analytics.md) | what is recorded about use |
| [What a month cost, and who pays](operations/chargeback.md) | attributing spend |

## Decisions

| | |
|---|---|
| [1. Durable execution](adr/0001-durable-execution.md) | Temporal, around Aegra |

---

Two of these are generated — [`harness`](reference/cli.md) from the command
parser and the [config reference](reference/config-reference.md) from the
Pydantic models. Edit the code, run `make cli-docs` or
`make config-reference`; CI fails if they drift.
