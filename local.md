# Run it

Three ways. Pick one.

| | what runs where | use it when |
|---|---|---|
| `make dev` | services on your machine, dependencies in containers | you are writing code |
| `make container` | everything in containers, with compose | checking the image before deploying |
| `make kind` | everything in a local Kubernetes cluster | checking the manifests |

---

## `make dev`: on your machine

```sh
make install    # python and the UI both; drops you in a subshell,
                # `exit` to come back
make doctor
make dev
```

`make dev` copies `.env.example` to `.env` if you have no `.env` yet.

Open http://localhost:5173

The agent and the UI reload from the working tree: uvicorn for one,
Vite for the other. Postgres, Redis and OPA run in containers; you do
not install them.

Stop: `Ctrl-C`. That leaves the dependencies up, because the next
`make dev` is ten seconds away and a Postgres restart is not. To stop
those too: `make deps-down`

---

## `make container`: everything in containers

```sh
make container
```

Open http://localhost:8080. The agent is on :5002 and Jaeger on
:16686. It writes `.env` from `.env.example` if you have none.

Builds the image and runs it the way the cluster will, so this is
where a "works on my machine" difference shows up first.

Stop: `make container-down`

---

## `make kind`: in a cluster

```sh
make kind
```

Open http://localhost:8081

Builds the image, loads it into a local Kind cluster and applies the
kustomize overlay, the same manifests OpenShift gets.

Stop: `make kind-down`

---

## What you get

| | |
|---|---|
| http://localhost:5173 | the chat UI (`make dev`) |
| http://localhost:8080 | the chat UI (`make container`) |
| http://localhost:8081 | the chat UI (`make kind`) |
| http://localhost:5002 | the agent API |
| http://localhost:5003 | the UI's BFF (`make dev` starts it with the UI) |

---

## It costs what it costs

`make dev` talks to the real model and the real MCP servers, the
ones `config/agent/integrations/mcp.json` names, each wanting a
credential. There are no stand-ins: an iteration bills, and a
server that is not connected says so rather than answering.

The model is whatever `config/agent` names. To run against a
different one, point `make dev` at another config tree:

```sh
make dev CONFIG=path/to/other/config
```

---

## Put some data in it

```sh
make seed
```

---

## Ask it something

```sh
.venv/bin/python -m agent.cli.main ask "what are you for?"
```

---

## When it breaks

```sh
make doctor
```

| it says | do this |
|---|---|
| port 5002 in use | `make dev-down` then `make dev` |
| Postgres never ready | `make deps-down` then `make dev` |
| no node_modules in services/ui | `make install` does the UI too |
| UI skipped | check there is a `services/ui` checkout |
| nothing works | `podman ps`: are the containers up? |

Logs: `.local/logs/` holds `agent.log` and `ui.log`
