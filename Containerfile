# One image, both roles (E10 strand D, T18). Two images let a
# deployment run agent v7 against interface v6 — the mismatch the
# shared version was supposed to make impossible. Here the role is
# the entrypoint's argument: `harness agent`, `harness ui`, or
# `harness all`.
#
#     podman build -f Containerfile --target runtime -t harness:local .
#
# Node's install and the UI build stay in their own stage, and
# Python's install happens before any application code is copied,
# so neither side's edits reinstall the other's dependencies.
#
# The cost: both runtimes in one image, and a CVE surface that is
# the union of the two.

# Both declared before the first FROM. An ARG belongs to the stage
# it is written in, and `COPY --from=${VENV_STAGE}` needs the
# global one to resolve to a stage — without it buildah tries to
# pull `docker://deps:latest`.
ARG VENV_STAGE=deps
ARG PYTHON_TAG=3.14.4-builder
# Not `3.14.4`, the 117MB runtime tag: it is distroless, and this
# stage must `dnf install nodejs24`. Its own ARG so the 76MB is
# visible if the Node half ever moves out.
ARG PYTHON_RUNTIME_TAG=3.14.4-builder

# ── the interface, built ────────────────────────────────────────
FROM registry.access.redhat.com/hi/nodejs:26.13.1-builder AS ui

WORKDIR /opt/app-root/src
USER root

COPY services/ui/package*.json ./
# Before the sources, so a component edit does not reinstall.
RUN npm ci

COPY services/ui/src ./src
COPY services/ui/public ./public
COPY services/ui/scripts ./scripts
COPY services/ui/components.json services/ui/eslint.config.js ./
COPY services/ui/vite.config.ts services/ui/vite-env.d.ts ./
COPY services/ui/tsconfig.json services/ui/tsconfig.node.json ./
RUN npm run build

# The server's dependencies, derived from its imports. Pruning
# devDependencies alone took 1.1GB to 915MB; the bulk is not dev
# but frontend libraries vite has already bundled into
# `dist/frontend` and the image then shipped again as source —
# @patternfly 313MB, monaco-editor 95MB. 22 of 50 dependencies are
# reachable from `src/server`.
#
# Derived rather than hand-written so the short list cannot drift
# from the long one. It also reports imports that are undeclared,
# which is how @opentelemetry/sdk-metrics turned out to be
# arriving as somebody else's transitive dependency.
RUN node scripts/server-deps.mjs \
    && mkdir -p /opt/server-deps \
    && cp package.server.json /opt/server-deps/package.json \
    && cd /opt/server-deps \
    && npm install --omit=dev --no-audit --no-fund --loglevel=error

# ── deps — the virtualenv, built where the compilers are ───────
# Split out so gcc and the headers do not ship.
FROM registry.access.redhat.com/hi/python:${PYTHON_TAG} AS deps

WORKDIR /app
USER root
COPY pyproject.toml /app/pyproject.toml
ENV UV_NO_CACHE=1

RUN pip install --no-cache-dir uv \
    && uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Debug symbols out of the compiled extensions: 419MB → 207MB,
# measured. Here rather than in `runtime` because `strip` is
# binutils. `|| true` because an already-stripped `.so` exits
# non-zero.
RUN (command -v strip >/dev/null 2>&1 \
      || microdnf install -y binutils --nodocs \
      || dnf install -y binutils) \
    && (find /app/.venv -name '*.so' -exec strip --strip-unneeded {} + 2>/dev/null || true)

# Test suites shipped inside wheels: 15MB for other projects' CI.
RUN find /app/.venv -type d -name tests -prune -exec rm -rf {} + 2>/dev/null || true

# ── deps-slim — the same venv without the PII model ────────────
#
# en_core_web_lg is 425MB, spaCy 124MB, presidio on top: 550MB to
# detect addresses with NER. All three are top-level dependencies
# (`uv tree --invert` shows nothing else reaching them), so this
# leaves no orphaned dependents.
#
# Uninstalled from a copy rather than never installed, because a
# layer only grows — deleting in `runtime` would save nothing.
#
# A slim image cannot do presidio-based PII detection at all.
# `pii.yaml`'s address rule uses it, and `PerRuleDetector` raises
# on the missing import rather than quietly scrubbing nothing.
FROM deps AS deps-slim

# `uv pip`, because `uv venv` installs no pip: `python -m pip
# uninstall` here fails, falls through to the system pip, and with
# a `|| true` builds a "slim" image the same size as the full one.
# Verified in the same layer for the same reason.
RUN uv pip uninstall --python /app/.venv/bin/python \
        en_core_web_lg spacy presidio-analyzer \
    && /app/.venv/bin/python -c "\
import importlib.util as u, sys; \
left = [m for m in ('spacy','presidio_analyzer','en_core_web_lg') if u.find_spec(m)]; \
sys.exit('still installed: ' + ', '.join(left)) if left else print('slim venv: the three are gone')"

# ── deps-eval — the venv plus the scoring stack ────────────────
#
# `lightspeed-evaluation` brings 39 packages the harness does not
# otherwise have, and 198MB of them: scipy 72, pandas 40,
# matplotlib 20, fonttools 14. Measured, not estimated — 110 of
# its 149 dependencies were already here.
#
# Its own stage so only the eval worker carries it. The agent and
# the interface have no use for scipy, and `harness eval-worker`
# is the one role that scores anything. Same pattern as
# deps-slim, one --build-arg apart.
FROM deps AS deps-eval

# A git+https requirement needs git, which the deps base does not
# carry. Without it `uv pip install` fails with "Git executable not
# found" — and this stage used to end `|| true`, which applied to
# the whole `&&` chain and turned that failure into a green build
# with no package in it. The import check below could not fire.
# `git` for the git+https requirement, and a C toolchain because
# pandas publishes no cp314 wheel at the version this pulls, so it
# builds from source. Both stay in this stage — runtime copies the
# finished venv, not the compiler.
RUN dnf install -y --setopt=install_weak_deps=False \
        git-core gcc gcc-c++ make python3.14-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN uv pip install --python /app/.venv/bin/python \
        "lightspeed-evaluation @ git+https://github.com/lightspeed-core/lightspeed-evaluation.git@v0.8.0" \
    && /app/.venv/bin/python -c "import lightspeed_evaluation; print('eval stack present')"

# Only the strip is allowed to fail; it is a size optimisation, not
# a requirement, and it is on its own line so its `|| true` cannot
# excuse anything above it.
RUN find /app/.venv -name '*.so' -exec strip --strip-unneeded {} + 2>/dev/null || true

# One stage whose only job is to resolve the build arg to a name
# `--from` will accept.
ARG VENV_STAGE
FROM ${VENV_STAGE} AS venv

# ── runtime — the image that serves either role ────────────────
FROM registry.access.redhat.com/hi/python:${PYTHON_RUNTIME_TAG} AS runtime

WORKDIR /app
USER root

# From the distribution, not copied out of the builder: `node`
# links against libnode, libuv, libcares and others, so lifting
# the binary alone builds an image that cannot start.
RUN dnf install -y --setopt=install_weak_deps=False nodejs24 \
    && dnf clean all \
    && rm -rf /var/cache/dnf

COPY pyproject.toml /app/pyproject.toml

# uv's cache is 1.4GB of build input with no runtime use.
ENV UV_NO_CACHE=1

# `--build-arg VENV_STAGE=deps-slim` → no spaCy, no presidio. One
# runtime stage either way; duplicating it for one COPY is how the
# two drift apart.
#
# The selection goes through the `venv` stage above rather than
# `COPY --from=${VENV_STAGE}` directly: buildkit refuses a variable
# there — "variable expansion is not supported for --from, define a
# new stage" — so the image built under podman and had never built
# in CI. `FROM ${ARG}` is expanded, `--from=${ARG}` is not.
COPY --from=venv /app/.venv /app/.venv

# `/app/data` group-writable and group 0, which is what the
# restricted SCC requires (DEP-1). It used to be created
# implicitly by the volume mount at `/app/data/documents`, so the
# parent came out root:root 755 and uid 65532 could not create
# `/app/data/current` — every graph build that needed it answered
# 500 with Permission denied, which read as missing model
# credentials. `tests/unit/deployment/` cannot catch this: those
# 102 tests read the manifests, and this is the image.
RUN mkdir -p /app/.cache /app/config/agent /app/services/ui /app/data && \
    chown -R 65532:root /app/.cache /app/config /app/services /app/data && \
    chmod -R g+rwX /app/data && \
    chown 65532:0 /app && chmod g+w /app

# The server is `dist/server/index.js`; `dist/client` is what it serves.
COPY --from=ui --chown=65532:root /opt/app-root/src/dist /app/services/ui/dist
COPY --from=ui --chown=65532:root /opt/server-deps/node_modules /app/services/ui/node_modules
COPY --chown=65532:root services/ui/package.json /app/services/ui/package.json

# Red Hat's internal root CA, appended to the bundle httpx reads.
# `httpx._config.create_ssl_context` ends in
# `ssl.create_default_context(cafile=certifi.where())` unless
# SSL_CERT_FILE or SSL_CERT_DIR is set, so update-ca-trust — the
# obvious move on a UBI base — changes nothing this process reads.
# Appended, not substituted: SSL_CERT_FILE replaces the bundle,
# and pointing it at the internal CA alone breaks the model API.
#
# Internal MCP servers (gitlab-mcp, gworkspace, unstructured-data)
# serve certificates signed by this CA. Without it the handshake
# fails and OAuth discovery reports that the server "does not
# publish OAuth metadata" — a sentence about the wrong layer.
COPY deployment/certs/Current-IT-Root-CAs.pem /etc/pki/ca-trust/source/anchors/
RUN cat /etc/pki/ca-trust/source/anchors/Current-IT-Root-CAs.pem \
      >> "$(/app/.venv/bin/python -c 'import certifi; print(certifi.where())')" && \
    /app/.venv/bin/python -c "import certifi,ssl; ssl.create_default_context(cafile=certifi.where()); print('certifi bundle loads')"

# And the same CA for Node, which certifi does not reach. The
# interface has its own trust store; its old standalone entrypoint
# set this, and that path was lost in the merge.
ENV NODE_EXTRA_CA_CERTS=/etc/pki/ca-trust/source/anchors/Current-IT-Root-CAs.pem

# `ui/src/server/utils/opa.ts` does `execFileSync("opa", …)`. Off
# by default, which is why it has to be here: a toggle that
# ENOENTs when somebody turns it on is worse than the 60MB.
ARG OPA_VERSION=1.22.1
RUN curl -fsSL "https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_amd64_static" \
      -o /usr/local/bin/opa \
    && chmod 755 /usr/local/bin/opa \
    && /usr/local/bin/opa version

USER 65532

COPY --chown=65532:root services/agent /app/services/agent
COPY --chown=65532:root aegra.json /app/aegra.json
COPY --chown=65532:root pyproject.toml /app/pyproject.toml

ENV PYTHONPATH=/app/services
ENV AGENT_HOST=0.0.0.0
ENV AGENT_PORT=5002
ENV AEGRA_CONFIG=/app/aegra.json
ENV CONFIG_PATH=/app/config/agent
ENV UI_DIR=/app/services/ui

EXPOSE 5002 8080

# No role baked in. A Deployment says which one it is.
ENTRYPOINT ["/app/.venv/bin/python", "-m", "agent.cli.main"]
CMD ["agent"]

# ── ci — the same image plus the test tooling (E26-T4) ─────────
#
#     podman build -f Containerfile --target ci -t harness:ci .
#
# Everything below `FROM runtime` is a layer on top, so "passes
# CI" and "works in production" cannot depend on two toolchains.
# `make ci-image-check` asserts the versions here match what the
# repository pins.
#
# Build the runtime image with `--target runtime`. A build with no
# target builds the last stage; when this was last, `harness:local`
# became the CI image and the agent pod crashed on
# `can't open file '/src/agent'`.
FROM runtime AS ci

USER root
COPY pyproject.toml /app/pyproject.toml
# `python -m pip install uv` inside the venv fails with "No module
# named pip" — `uv venv` installs none. uv itself is already here.
RUN uv pip install --python /app/.venv/bin/python \
       --extra dev -r /app/pyproject.toml
USER 65532

# The tests are mounted, not copied — baked in they would go stale
# the moment anybody edits one, and the image would depend on what
# it is testing. Reproducing a CI failure locally:
#
#     podman run --rm -v "$PWD:/src:ro" -w /src harness:ci \
#         -m pytest tests/unit -q
WORKDIR /src
ENTRYPOINT ["/app/.venv/bin/python"]
CMD ["-m", "pytest", "tests/unit", "-q"]

# ── config — the configuration tree as its own tiny image ──────
#
# Built with `--target config`. The config-pvc component unpacks
# it into the volume the agent reads, so a prompt change is a
# config build rather than an application build. A stage rather
# than the old Containerfile.config, which was a second thing to
# keep in step with the base it derived from.
FROM runtime AS config

COPY --chown=65532:root config/agent /app/config/agent

# ── default — what a build with no `--target` produces ─────────
#
# A plain build produces the last stage, and OpenShift's
# dockerStrategy has no target field. With `config` last, both
# BuildConfigs shipped the configuration image as the agent: a
# container that starts, has the right entrypoint, and is the
# wrong artifact.
FROM runtime AS default
