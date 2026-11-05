# Template Agent

[![Python 3.13+](https://img.shields.io/badge/python-3.13,3.14-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/redhat-data-and-ai/template-agent/actions/workflows/test.yml/badge.svg)](https://github.com/redhat-data-and-ai/template-agent/actions/workflows/test.yml)
[![CodeQL](https://github.com/redhat-data-and-ai/template-agent/actions/workflows/codeql.yml/badge.svg)](https://github.com/redhat-data-and-ai/template-agent/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/redhat-data-and-ai/template-agent/badge)](https://securityscorecards.dev/viewer/?uri=github.com/redhat-data-and-ai/template-agent)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A **harness for running agents in production** — the part that is the
same whatever your agent does.

Most agent projects start with a graph and a model call, and then spend
months rebuilding the same scaffolding: a chat interface, identity,
authorisation, conversation persistence, scheduled work, tool
integration, observability, evaluation, a deployment. This is that
scaffolding, already built and already measured, with one well-marked
seam where your agent goes.

Swap the prompt, the subagents and the skills in `config/agent/` and it
is your product. Nothing below that line assumes what the agent is for.

## What you get that you would otherwise write

| | |
|---|---|
| **Interface** | React chat UI with projects, spaces, scheduling, analytics and an admin console — same repository, same version, same image as the agent |
| **Identity and authorisation** | OIDC sign-in, LDAP group-to-role mapping, OPA policies, per-user rate limits, PII scrubbing |
| **Persistence** | Postgres checkpoints, conversation memory, feedback, artifacts; Redis/Valkey for streaming |
| **Scheduled and long-running work** | Cron schedules bound to their own conversation, and Temporal-backed durable execution for jobs measured in weeks |
| **Tools** | MCP registry with SSO pass-through, OAuth and DCR; interactive `ui://` apps |
| **Evaluation** | Offline and live eval harnesses, LLM-as-judge checks, drift tracking, dataset APIs |
| **Observability** | OpenTelemetry metrics and traces, Langfuse, cost and token accounting, SLOs |
| **Deployment** | One image serving every role, kustomize overlays for Kind and OpenShift, hardened base images |
| **Proof it works** | 5,100+ UI tests, a large Python unit suite, mocked and live end-to-end suites, and a k6 load suite at 80 concurrent users |

## The one-image idea

Agent, interface and worker are **one image and one tag**, with the
role chosen by the entrypoint:

```
harness agent     the API
harness ui        the interface
harness worker    durable execution
harness opa       the policy engine, from the config tree
harness all       every role this deployment wants, in one container
```

Two images let a deployment run version 7 of the agent against version 6
of the interface. One cannot. Every Deployment names the same image, and
`make kind-roll` moves them together.

`harness opa` is the clearest case for this. The image already carried
the `opa` binary — the interface compiles policy to wasm with it — and
the policies already live in `config/agent/compliance/policies/`, so a
separate policy Deployment meant a second image to build and a git sync
that was a second source of truth for the same `.rego` files. The
agent's `opa.url` had defaulted to `localhost:8181` all along.

## Where your agent goes

```
config/agent/
├── PROMPT.md       the orchestrator's instructions
├── subagents/      who it can delegate to
├── skills/         named workflows and their guardrails
├── mcp.json        which tools exist and how they authenticate
└── runtime/        models, memory, limits, features
```

Config-as-code, editable in the UI and on disk, with a drift check that
fails CI when the two disagree. Most changes need no Python.

## Quick Start

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/), [Podman](https://podman.io/), Google Vertex AI credentials

```bash
git clone https://github.com/redhat-data-and-ai/template-agent.git
cd template-agent
make install     # creates venv, installs deps + pre-commit hooks
make dev       # pgvector + redis in compose; agent on host → :5002
```

`make install` sets up pre-commit hooks (`gitleaks` and `detect-private-key`). Also enable [GitHub Secret Scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning) and [Push Protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection) on the repository for defense in depth.

Verify in another terminal:

```bash
curl http://localhost:5002/health
```

Copy `.env.example` to `.env` before first run (or let `make dev` create it) and set `GOOGLE_APPLICATION_CREDENTIALS_CONTENT`.

**The interface lives in `ui/`**, in this repository, and ships in the same image. Only the example MCP server is separate — clone [template-mcp-server](https://github.com/redhat-data-and-ai/template-mcp-server) if you want it; the agent reaches real MCP servers over the network either way.

## API

The agent exposes the standard **LangGraph API** (assistant ID: `agent`, defined in `aegra.json`) plus custom routes on the Aegra HTTP app.

### LangGraph API

| Endpoint | Method | Description |
|---|---|---|
| `/ok` | GET | Server health |
| `/assistants/{assistant_id}` | GET | Assistant metadata |
| `/threads` | POST | Create conversation thread |
| `/threads/{thread_id}` | GET | Get thread state |
| `/threads/{thread_id}/runs` | POST | Run agent (sync) |
| `/threads/{thread_id}/runs/stream` | POST | Run agent (SSE stream) |

```bash
# Create a thread
curl -X POST http://localhost:5002/threads \
  -H "Content-Type: application/json" \
  -d '{}'

# Stream a message (replace THREAD_ID)
curl -N -X POST "http://localhost:5002/threads/THREAD_ID/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {"messages": [{"role": "human", "content": "Hello"}]},
    "stream_mode": "updates"
  }'
```

### Custom routes

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (also `/healthz`, `/readyz`, `/livez`) |
| `/info` | GET | Agent name and OAuth/DCR MCP server list |
| `/feedback` | POST | Record user feedback (Langfuse + Postgres) |
| `/feedback/{thread_id}` | GET | List feedback for a thread |
| `/threads/{thread_id}/token-usage` | GET | Cumulative token usage for a thread |
| `/mcp/{name}/connect` | POST | Start OAuth/DCR flow for an MCP server |
| `/mcp/oauth/callback` | GET | OAuth redirect handler |
| `/mcp/{name}/status` | GET | MCP connection status for current user |
| `/mcp/{name}/resources/read` | POST | MCP Apps: read a `ui://` resource |
| `/mcp/{name}/tools/call` | POST | MCP Apps: app-initiated tool call |

Use [template-ui](https://github.com/redhat-data-and-ai/template-ui) for a full chat experience against this API.

## Configuration

Configuration is split between **secrets/endpoints** (`.env`) and **operational settings** (`config/agent/runtime/agent.yaml`).

### Environment variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | Postgres host (`pgvector` in compose) |
| `POSTGRES_PORT` | `5432` | Postgres port |
| `POSTGRES_DB` | `template_agent` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (required for OAuth/DCR MCPs) |
| `REDIS_BROKER_ENABLED` | `true` | Enable Redis-backed SSE broker |
| `GOOGLE_APPLICATION_CREDENTIALS_CONTENT` | — | Inline service account JSON (used when set; ADC is the fallback) |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to ADC file (used when CONTENT is unset; set automatically in discover-agent-deploy compose) |
| `ENABLE_AUTH` | `false` in `.env.example` | SSO/OIDC authentication |
| `SSO_ISSUER_URL` | — | OIDC issuer (Keycloak, Okta, etc.) |
| `SSO_CLIENT_ID` | — | OIDC client ID |
| `SSO_CLIENT_SECRET` | — | OIDC client secret |
| `LDAP_URL` | — | LDAP server URL (e.g. `ldaps://ldap.example.com`). Required when PROMPT.md has groups |
| `LDAP_BASE_UID` | — | Service account uid for LDAP bind |
| `LDAP_PASSWORD` | — | Service account password |
| `LDAP_GROUP_SEARCH_BASE` | `ou=adhoc,ou=managedGroups,<baseDn>` | Override group search subtree |
| `LDAP_TLS_VERIFY` | `true` | Validate LDAP server TLS certificate |
| `LDAP_CACHE_TTL_SECONDS` | `300` | Redis cache TTL for LDAP membership lookups |
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse public key (optional) |
| `LANGFUSE_SECRET_KEY` | — | Langfuse secret key (optional) |
| `LANGFUSE_BASE_URL` | — | Langfuse host (optional) |
| `LANGFUSE_TRACING_ENVIRONMENT` | `development` | Langfuse environment label |
| `MCP_TOKEN_ENCRYPTION_KEY` | — | Fernet key for OAuth/DCR token encryption |
| `MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS` | — | Previous key during rotation (decrypt-only) |
| `AGENT_PUBLIC_BASE_URL` | `http://localhost:5002` | Public agent URL for OAuth callbacks |
| `CUSTOM_CA_FILE` | — | Host path to a PEM file with custom CA certs (compose only) |
| `SSL_KEYFILE` | — | TLS private key path (optional) |
| `SSL_CERTFILE` | — | TLS certificate path (optional) |
| `OPA_ENABLED` | `true` (agent.yaml) | Enable/disable OPA authorization middleware |
| `OPA_URL` | `http://opa:8181/v1/data/agent/authz` | OPA policy decision endpoint |
| `OPA_TIMEOUT` | `2.0` | OPA request timeout in seconds (fails open on timeout) |
| `OPA_MAX_RETRIES` | `3` | Max model retries when output is blocked by OPA |
| `OPA_POLL_INTERVAL` | `2` | Seconds between policy hot-reload polls |

See [`.env.example`](./.env.example) for the full list including OpenTelemetry and MongoDB token-usage settings.

Runtime settings (cache, memory, providers, middleware, agent identity) live in [`config/agent/runtime/agent.yaml`](./config/agent/runtime/agent.yaml).

## OPA (Authorization)

An [Open Policy Agent](https://www.openpolicyagent.org/) sidecar enforces authorization policies on every LLM response, tool result, and conversation trajectory. It starts automatically with `make dev` and is included in the default `compose.yaml`.

The `opa:` section in `agent.yaml` and the `OPA_*` environment variables above configure the agent-side client. Local policies live in `config/agent/compliance/policies/` and can be augmented from a remote git repository with automatic hot-reload.

See **[`opa/README.md`](./opa/README.md)** for a full explanation of how the middleware, service, config, and OPA container work together.

## LDAP Access Control

Role-based access control driven by LDAP group membership. Group-to-role mappings are defined in [`config/agent/PROMPT.md`](./config/agent/PROMPT.md) YAML front matter — no code changes needed to add or remove groups.

### Role hierarchy

| Role | Priority | Chat | Eval / Dataset |
|---|---|---|---|
| `owners` | 4 | Yes | Yes |
| `admins` | 3 | Yes | Yes |
| `builders` | 2 | Yes | Yes |
| `users` | 1 | Yes | No (403) |
| `denied` | — | No (403) | No (403) |

When a user belongs to multiple groups, the highest-priority role wins.

### PROMPT.md configuration

Groups and accessibility are set in the YAML front matter of `config/agent/PROMPT.md`:

```yaml
---
accessibility: public
groups:
  - role: owners
    group: aifactory-template-owner
  - role: admins
    group: team-admins
  - role: builders
    group: team-builders
  - role: users
    group: team-users
---
```

### Behavior matrix

| Scenario | Chat (`/threads/*`, `/runs/*`) | Eval (`/evals/*`, `/v1/eval/*`) |
|---|---|---|
| `ENABLE_AUTH=false` | Full access | Full access |
| No groups in PROMPT.md | Allowed | 403 (everyone is `users`) |
| Groups + role `owners`/`admins`/`builders` | Allowed | Allowed |
| Groups + role `users` | Allowed | 403 |
| Groups + no match + `accessibility: private` | 403 (denied) | 403 (denied) |
| Groups + no match + `accessibility: public` | Allowed (as `users`) | 403 |
| Groups defined + `LDAP_URL` missing | Depends on accessibility | 403 |

### How it works

1. User authenticates via SSO/OIDC — the JWT `preferred_username` claim identifies the user.
2. The agent reads group-to-role mappings from PROMPT.md front matter (cached with mtime-based invalidation).
3. For each configured group, the agent queries LDAP to check if the user is a member (`member`, `uniqueMember`, or `memberUid` attributes).
4. The highest-priority matching role is assigned. If no groups match, the role is `denied` (private) or `users` (public).
5. LDAP results are cached in Redis (with in-memory fallback) for `LDAP_CACHE_TTL_SECONDS` (default: 300s).

### Two enforcement layers

- **LangGraph auth** (`services/agent/aegra/auth.py`): gates chat endpoints (`/threads/*`, `/runs/*`). Raises `PermissionError` for `denied` role — blocks the conversation entirely.
- **FastAPI dependencies** (`services/agent/aegra/eval_routes.py`): gates eval and dataset endpoints. Requires `owners`, `admins`, or `builders` role — returns HTTP 403 for `users` or `denied`.

### Setup

1. Define groups in `config/agent/PROMPT.md` front matter (see example above).
2. Set LDAP environment variables in `.env`:

```bash
LDAP_URL=ldaps://ldap.example.com
LDAP_BASE_UID=svcacct
LDAP_PASSWORD=your-password
# Optional:
# LDAP_GROUP_SEARCH_BASE=ou=adhoc,ou=managedGroups,dc=example,dc=com
# LDAP_TLS_VERIFY=true
# LDAP_CACHE_TTL_SECONDS=300
```

3. Set `ENABLE_AUTH=true` and configure SSO variables.

When `ENABLE_AUTH=false` (dev mode), LDAP is skipped entirely and all endpoints are accessible.

## MCP Server Configuration

MCP servers are defined in [`config/agent/integrations/mcp.json`](./config/agent/integrations/mcp.json) and attached to agents via the `mcps` frontmatter field in [`config/agent/PROMPT.md`](./config/agent/PROMPT.md) (orchestrator) or [`config/agent/subagents/*.md`](./config/agent/subagents/).

### Auth modes

| `auth_mode` | When to use | How credentials work |
|---|---|---|
| `sso` (default) | MCP accepts the same SSO token as the agent | User Bearer token forwarded on every tool call |
| `oauth` | MCP has a pre-registered OAuth client | User connects via chat UI; tokens stored encrypted in Redis |
| `dcr` | MCP supports OAuth Dynamic Client Registration | Agent registers at connect; per-user OAuth flow follows |

Set `"auth": false` for public/local MCP servers with no Authorization header.

### MCP Apps (interactive UI)

The agent advertises the MCP Apps UI extension on `initialize` and exposes host proxy routes used by Template UI:

| Endpoint | Method | Description |
|---|---|---|
| `/mcp/{name}/resources/read` | POST | Read a `ui://` Apps resource (HTML) |
| `/mcp/{name}/tools/call` | POST | App-initiated tool call (`visibility` must include `app`) |

Add any SEP-1865-compliant App server to `mcp.json` the same way as a normal MCP — no agent code changes.

Compliance smoke tests:

```bash
.venv/bin/python -m pytest tests/unit/aegra/test_mcp_apps_smoke.py -q
```

### MCP URL by run mode

| Mode | `url` in `mcp.json` |
|---|---|
| `make dev` (agent on host) | `http://localhost:5001/mcp` (default) |
| `make container` (MCP on host) | `http://host.containers.internal:5001/mcp` |

Alternate URLs are provided as `//` comments in `mcp.json` — uncomment the line you need.

### Wiring MCPs to agents

```yaml
---
name: analyst
model: gemini-2.5-pro
mcps:
  - template-mcp-server
tools:
  - calculate_bmi
  - search_web
---
```

- **Orchestrator:** add `mcps:` to `config/agent/PROMPT.md` frontmatter.
- **Subagent:** add `mcps:` to `config/agent/subagents/<name>.md` frontmatter.
- **Inheritance:** subagents without `mcps` inherit the orchestrator's list.
- **Validation:** every name in `mcps` must exist in `mcp.json` with `enabled: true`.
- **Resources:** optional `resources:` list of URI / `uriTemplate` strings (not resource names). Omit the key (or pass `[]`) to allow all URIs on the agent's MCP servers; list specific URIs to allowlist. Subagents without `resources:` inherit the orchestrator's list. Server scope follows `mcps:` if set, otherwise all enabled servers in `mcp.json`.

```yaml
resources:
  - template://about
  - template://echo/{text}
```

See `config/agent/integrations/mcp.json` for working SSO and DCR examples.

### Tool name prefix

When multiple MCP servers are configured, tool names are prefixed with the
server key (e.g. `search_mcp_prod_search_web`). Add `tool_prefix` to use a
shorter prefix:

```json
{
    "mcpServers": {
        "search-mcp-prod": {
            "url": "http://search:9090/mcp",
            "transport": "streamable_http",
            "enabled": true,
            "auth": true,
            "tool_prefix": "search"
        }
    }
}
```

## Project Structure

```
template-agent/
├── aegra.json                  # Aegra / LangGraph framework entry point
├── config/agent/
│   ├── PROMPT.md               # Orchestrator prompt + frontmatter
│   ├── subagents/              # Subagent definitions
│   ├── skills/                 # Skill documents and evals
│   ├── mcp.json                # MCP server registry
│   ├── runtime/agent.yaml      # Runtime config (cache, memory, providers)
│   └── deployment/values.yaml  # OpenShift/ArgoCD deployment reference values
├── services/agent/
│   ├── aegra/                  # Graph, HTTP app, MCP OAuth, entrypoint
│   └── src/                    # Config loader, cache, memory, token budget, etc.
├── ui/                         # The interface: React SPA + Fastify BFF
│   ├── src/frontend/           # The SPA
│   ├── src/server/             # The BFF that fronts it
│   ├── e2e/                    # Playwright, agent mocked
│   └── e2e-live/               # Playwright, against a running stack
├── test/load/                  # k6: 80 heavy users, mixed and per-feature
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Aegra integration and e2e tests
│   └── skills/                 # LLM-as-judge skill evaluations
├── compose.yaml                # Postgres + Redis (+ agent with --profile container)
├── Containerfile
└── deployment/                 # OpenShift and Kind overlays
```

## Testing

```bash
make test           # unit tests
make test-all       # unit + skills evals
make test-skills    # skills evaluations only
make test-cov       # unit tests with coverage
```

Skills evals auto-discover from `config/agent/skills/*/evals/evals.json`. See [`config/agent/evals/README.md`](./config/agent/evals/README.md) for Promptfoo and Lightspeed eval options.

```bash
# Code quality
ruff check . && ruff format .
pre-commit run --all-files
```

## Custom CA Certificates

If your environment uses a corporate or internal certificate authority, the container can trust it at startup without rebuilding the image.

**Red Hat internal** — the Kind overlay already sets this, and it is what
lets the agent reach internal MCP servers and any other internal HTTPS
dependency:

```yaml
- name: CUSTOM_CA_URL
  value: "https://certs.corp.redhat.com/certs/Current-IT-Root-CAs.pem"
```

Without it, internal hosts fail the TLS handshake with
`CERTIFICATE_VERIFY_FAILED: self-signed certificate` — which looks like
the server being down rather than a trust problem. On OpenShift set
`CUSTOM_CA_URL` in the `agent-config` ConfigMap.

The bundle is fetched over HTTPS **verified against the system trust
store**; a CA pulled over an unverified connection would be
trust-on-first-use, which is not trust. A failed fetch logs a warning
and start-up continues.

**Compose** — set `CUSTOM_CA_FILE` in `.env` to the host path of your PEM bundle:

```bash
# .env
CUSTOM_CA_FILE=./certs/ca.pem
```

**Kubernetes** — create a Secret and mount it, then set `CUSTOM_CA_PATH`:

```yaml
env:
  - name: CUSTOM_CA_PATH
    value: /etc/custom-ca/ca.pem
volumeMounts:
  - name: custom-ca
    mountPath: /etc/custom-ca
    readOnly: true
volumes:
  - name: custom-ca
    secret:
      secretName: custom-ca
```

**Fallback URL** — for non-orchestrated environments (e.g. `podman run`), set `CUSTOM_CA_URL` to download the PEM at startup:

```bash
podman run -e CUSTOM_CA_URL=https://certs.example.com/ca.pem ...
```

If neither variable is set, or the download fails, the container starts normally with default system certs.

## Deployment

```bash
make container
```

For production: configure TLS (`SSL_KEYFILE`, `SSL_CERTFILE`), use managed PostgreSQL and Redis, set `AGENT_PUBLIC_BASE_URL` to your HTTPS URL, and enable Langfuse tracing.

OpenShift manifests are in `deployment/overlays/openshift/`. Local full-stack Kubernetes testing: `make kind`.

## Links

- [Skills](docs/guides/skills.md) — building skills from prose corpora and datasets
- [Observability](docs/operations/observability.md) — where each signal goes, and the keys that join them
- [SLOs](docs/operations/slo.md) — the four SLIs; targets are yours to set
- [Runbook](docs/operations/runbook.md) — symptoms, releases, rollbacks
- [Postmortem template](docs/operations/postmortem.md) — copy per incident
- [Document extraction](docs/guides/extraction.md) — optional Docling/Tika engines
- [Usage analytics](docs/operations/analytics.md) — `/analytics/*`, derived, no message content
- [Tags and sharing](docs/guides/tags-and-sharing.md) — organising and publishing conversations
- [Issues](https://github.com/redhat-data-and-ai/template-agent/issues)
- [template-mcp-server](https://github.com/redhat-data-and-ai/template-mcp-server)
- [template-ui](https://github.com/redhat-data-and-ai/template-ui)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)

## License

[Apache 2.0](LICENSE)
