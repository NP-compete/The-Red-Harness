# The inner loop

Clean machine to a streamed token, and what to reach for when the
fast loop stops being enough.

## From nothing

```sh
./misc/scripts/install-mac.sh     # once, from the workspace root
make doctor                       # what is missing, before it fails
make dev                           # dependencies, agent, interface
```

`make dev` starts Postgres, Redis and OPA in podman, then the agent
on :5002, the BFF on :5003 and Vite on :5173, and tails both logs.
Ctrl-C stops what it started and leaves the dependencies running,
because the next `make dev` is ten seconds away and a Postgres
restart is not.

The model is a stub on :5004 by default. It costs nothing, answers
deterministically, and echoes the question back so a wiring bug
cannot look like a working agent. `make dev MODEL=vertex` uses
whatever `config/agent` names, and bills for it.

```sh
make seed            # a user, a thread with history, a space, a token
make dev-wait         # wait for all four to answer, and say what did not
make dev-down         # stop the loop, keep the dependencies
```

## The three loops, and when to step up

| | What it covers | Cost |
|---|---|---|
| `make dev` | Everything that is code or configuration in these two trees | seconds |
| `make ci` | What a pipeline would say, locally | minutes |
| `make kind-sync` | Manifests, probes, ingress — anything only a cluster has | 48s for config, 106s with a rebuild — and a cluster |

Stay in the first one. The second is for a change you are about to
push; the third is for a change a laptop cannot be wrong about in
the right way — a readiness probe, an ingress rule, an SCC.

The cluster comes from `make kind` (add `WITH_MCP=1` for the
example MCP server, which needs git and the network). After that
`make kind-sync` is the small step:

```sh
make kind-sync             # config onto the volume, pods rolled — the default
make kind-sync WHAT=agent  # rebuild and roll the agent
make kind-sync WHAT=ui     # rebuild and roll the interface
make kind-sync WHAT=all    # both, and the config
```

Measured on this machine, not estimated:

| | Target | Measured |
|---|---|---|
| `make kind-sync` (config) | 90s | **47.7s** |
| `make kind-sync WHAT=agent` (rebuild and roll) | 90s | **106.2s** |

Most of the first is one agent startup. The second is over the
target and the page says so: a code change costs an image build
on top of the startup, and DX-3's 90 seconds is a number the
rebuild path does not meet. The figure here was 88s for both
until it was measured again — the config case had got faster and
the rebuild case had never been timed separately.

Two things in the kind overlay keep the first number where it is
and are worth not undoing: one replica (`maxUnavailable: 0` makes
a rollout sequential, so two replicas is two startups) and a
30-second termination grace instead of the production 600.

## With no Python and no Node installed

`make dev` is for people with the toolchain: it runs the agent
from `.venv` and the interface from `npm run dev`. A
configuration author has neither, and does not want them.

```sh
make kind     # podman, kind, kubectl, git — and nothing else
```

It builds the image and deploys agent, interface and
dependencies into the cluster, so the whole thing runs with no
interpreter on the machine. Measured rather than asserted: the
recipe contains no `.venv`, no `npm` and no `python3`, and
`tests/unit/test_the_inner_loop.py` fails if one appears —
a single `.venv/bin/python scripts/…` line added to that target
would take the toolchain-free path away silently, and the person
it was for is not the person who would notice.

It is minutes, not seconds. That is the trade: `make dev` is the
loop, `make kind` is the way in without installing anything.

## Against another configuration tree

The agent resolves everything under `CONFIG_PATH`, so the loop can
run against a tree that is not this repository's:

```sh
make dev CONFIG=config/bench        # the measurement tree
make dev CONFIG=~/their-deployment  # somebody else's
```

Relative paths resolve against the agent directory, because that
is what typing `config/bench` means. Verified by what comes back:
started against `config/bench`, `/admin/config` reports
`effects: dry_run` and no MCP servers, and `make bench-check`
agrees the agent is safe to measure against. Started against the
default tree it reports `effects: live`.

## How long it takes, and what to do when it drifts

```sh
scripts/dev/timings.sh             # measure, non-zero on a regression
scripts/dev/timings.sh --record    # and append to .local/timings.jsonl
```

It appends a comment to a module, waits for the agent to say
`Application startup complete` in its own log, and removes the
comment again. Measured on this machine:

| | Target | Measured |
|---|---|---|
| Agent reload | 5s | **6.1s** |
| Interface response | 1s | 0.05s |

**The agent reload was 20.4s until recently**, and the cause was
not import time. A reload is a shutdown, so the fifteen seconds
production spends draining in-flight runs was being paid on every
keystroke. `make dev` now sets `SHUTDOWN_DRAIN_SECONDS=0`: nothing
is in flight on a laptop between two edits, and a deployment that
wants the drain sets it back. The remaining six seconds is the
application starting, and it is over the target — stated rather
than rounded down.

Two earlier versions of that probe measured nothing and said they
passed. "Is `/health` up" always answers, because the reloader
keeps the socket while it replaces the worker — 96ms, measuring
one curl. "Has the pid on the port changed" never fires, because
that pid belongs to the reloader. The server's own "serving
again" line is the only honest signal from outside.

## One more thing worth knowing about this checkout

The agent is started as `.venv/bin/python .venv/bin/aegra`, not as
`.venv/bin/aegra`. A venv that was copied or relocated keeps the
shebang of the tree it was built in — this one pointed at another
checkout's interpreter, so the loop ran *this* tree's source (cwd
wins on `sys.path`) against *that* tree's installed packages.
Everything worked, which is the problem: a dependency difference
between the two would show up as behaviour the tests here cannot
reproduce.
