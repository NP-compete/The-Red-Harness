# Being called by another system

This agent can be reached by other systems the way it reaches
them. That is the inbound direction, and it is configured in
`config/agent/integrations/mcp_server.yaml`. It ships off.

## Why this is a layer, not a change to the runtime

The runtime this is built on lists inbound serving as coming
soon. Waiting for it would have meant waiting; changing the
runtime would have meant a fork to maintain against every
upstream release.

So this is built **over the protocol the runtime already
speaks**, not inside it. Nothing here edits runtime source. The
cost of being wrong is then an adapter to delete rather than a
fork to unpick, and the configuration surface can stay the same
across the swap.

This is the single most important thing to know before changing
any of it. An adapter that reaches into runtime internals to save
a few lines stops being removable, and the reason this was
acceptable to build at all disappears with it.

## If the capability arrives upstream

### Remove

- `services/agent/aegra/mcp_server_routes.py` — the whole inbound
  endpoint, including the adapter that turns a published tool
  into a run and the one that turns a pause into a result.
- Its line in `http_app.py`, and its tests.

That list is short on purpose. The adapter starts a run by
calling the run API over the loopback, exactly as any other
client does, so none of it leaks elsewhere: no branch inside the
graph, no second authorization site, no reader of runtime
internals. Deleting the file leaves a working agent that no
longer answers the door.

### Keep

- `config/agent/integrations/mcp_server.yaml` and the model that
  reads it. The questions it asks — is this open, whose authority
  does a call carry, which tools are published — are the same
  questions whatever serves them, and a deployment should not
  have to rewrite its configuration because the implementation
  underneath changed.
- The refusal to start when enabled with no auth mode.
- The absence of an agent-credentials mode. Upstream may not make
  that choice, and it is ours to keep.
- The declared-tools rule. An upstream default of publishing
  everything would be a wider interface than anybody asked for.

### Check before deleting anything

- That the upstream implementation carries the **caller's**
  identity rather than the service's. If it does not, this layer
  stays, because that is the whole point of it.
- That a run which pauses for approval returns a result a
  non-interactive caller can act on, rather than hanging.

## Whose authority a call carries

Two acceptable answers, and they are the entire set:

| Mode | The run behaves as | For |
|---|---|---|
| `oauth` | the calling person | somebody at a keyboard somewhere else |
| `service_token` | a service identity with its own, narrower policy | automation with nobody behind it |

There is no mode in which an inbound call runs on the agent's own
credentials. It would make the agent a confused deputy with every
connected integration behind it: a caller who could reach the
door could reach everything the deployment had ever connected,
without ever holding a credential for any of it.

That is not a setting that is refused. It is a setting that does
not exist, and a test asserts its absence so it cannot be added
by accident.

## What one caller may use

Authority answers *what* a caller may do. It says nothing about
*how much*, and an inbound caller is a program: a loop with a bug
does not get bored and go away. It exhausts the shared model
budget in minutes, and everybody else — including the people using
the interface — gets the failure.

Two limits, per caller, under `mcp_server.limits`:

| Setting | Catches |
|---|---|
| `per_second` and `burst` | a caller going too fast |
| `daily_spend` | a caller going at exactly the agreed rate and spending the month's budget by Thursday |

Both are needed. A rate limit alone bounds how often, never how
much, and the two failures look nothing alike from the outside.

Keyed on the verified identity on the request, never a claimed
one: a budget keyed on an unchecked `sub` lets any caller exhaust
another caller's allowance by saying it was them. A caller the
agent cannot identify is refused once limits are on, because one
shared bucket for every anonymous caller is a limit on nobody.

The counter lives in Redis, keyed by caller and day, so every
replica sees the same total — a counter in the process would
refuse a caller on whichever pod had been counting and admit it on
the rest. It fails open: refusing every caller because the counter
is unreadable turns an accounting problem into an outage, and this
is a budget guard rather than an access check.

Only requests that start work are gated. Somebody over their
budget can still read the run they already paid for.

## What the run is actually given

The table above says which mode a call runs under. This is what
that produces, decided once before anything starts:

| | `oauth` | `service_token` |
|---|---|---|
| The run's identity | the caller | `service:` and the caller |
| Their connected integrations | apply | never |
| Attributed to | the caller | the caller |

The prefix is the defence, not a label. Without it a service
token whose subject happened to equal a person's id would be
handed that person's connections — the deputy again, reached by
being named after somebody rather than by configuration. With it,
a service identity cannot occupy a person's namespace whatever it
is called.

Scope narrows this further and never widens it. A tool declared
`read` uses no connections even for a person who has them, and
`act` on a service identity is still none.

There is no mode that produces an empty identity either. An empty
one is the agent's own namespace, which is the same failure by a
third route.

## Being delegated to by another agent

The same door, a different dialect. A peer fetches a card saying
what this agent is, then hands it work.

| | |
|---|---|
| The card | `GET /.well-known/agent-card.json` |
| The work | `POST /a2a`, method `message/send` |

The card comes in two halves, which the protocol allows for. A
peer has to read how to authenticate before it can, so the public
half carries the name, the address and the security schemes — and
**no capabilities**, because what a deployment does is not a
public advertisement. An identified peer gets the declared list,
and the card says that half exists so a peer does not read an
agent with no skills and go away.

The capabilities on the card are the declared tools and nothing
else. A card that changed when somebody added a skill would break
peers exactly as silently as a tool list that did.

A task that stops for a human comes back as `input-required`,
which is the state the protocol already has for it, carrying the
context to resume.

**It calls the same authority function the other dialect does.**
Not a copy of it. A second place answering "whose run is this"
drifts from the first, and the one that drifts is the one nobody
is watching — so a test asserts both files reach for the same
function rather than trusting that they do.
