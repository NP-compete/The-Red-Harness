# The pipeline

Every job is a make target, so the list a pull request runs and
the list you can run are one list:

```sh
make ci              # the whole pull-request pipeline, locally
make ci JOB=test     # one job
make ci-jobs         # what the list is
```

If a job here is not a make target, that is the bug — fix the
workflow, not this page.

## What runs, and what it gates

| Job | Target | What it is for | When it fails |
|---|---|---|---|
| Configuration tree | `make validate-config` | The shipped tree still loads against this build's models | A field was renamed or removed without a migration. See `docs/compatibility.md` |
| Deployment overlays | `make render-deployment-check` | Overlays match `values.yaml` | Somebody edited a rendered file instead of its input. Re-render |
| Offline evals | `make evals-offline` | Retrieval quality against the corpus in the tree | A score fell further than the noise either run carried. Not on a first run, not on an improvement |
| Contract | `make test-contract` | The OpenAPI baseline matches the app | A route or payload changed. `make openapi-baseline`, then regenerate the UI's types |
| Deployment manifests | `make test-deployment` | SCC, probes, non-root, resource limits | A manifest lost a constraint the cluster will reject at apply time |
| Unit suite | `make test` | Everything else | Read the failure; it is a test |
| Pre-commit | `make pre-commit` | Formatting and lint | Run it locally; most of it fixes itself |

The first five are seconds, not minutes, and run as their own job
on purpose: a contract break should not wait behind coverage
instrumentation to be reported.

## `make ci` passes, and it did not an hour ago

Worth knowing, because the debt it carried had been there long
enough to look permanent: eighteen mypy findings across fourteen
files and eight pydocstyle ones. CI runs `pre-commit run
--all-files`, the same command, so the pipeline was red for the
same reason and had been for a while.

They were mostly one line each — a missing return annotation, a
value typed `Any` escaping a declared return, a method without a
docstring. Two were worth the reading: `graph_model.py` called
`seen.add(...)` inside an `or` arm, which works and reads as
though the call returned something, and `my_data_routes.py` used
one variable for two unrelated store types in one function.

If you add to it, expect the same treatment. A check that is
already failing teaches people to ignore the one that starts
failing — and the second one is usually the real bug.

## Jobs that are not in `make ci`

Release signing, SBOM and provenance (`package-release.yml`),
image builds, the licence scan and the OpenSSF scorecard. They
need registry credentials, a tag, or the network, so they run in
the pipeline and not on a laptop. `make ci` says what it skipped
rather than passing silently.

## The two local environments, and what only runs in one

```sh
make ci               # the checks that need nothing
make ci ENV=compose   # and the ones that need the datastores
make ci ENV=kind      # and the ones that need a cluster
```

The job list is the same sentence either way. `make ci-skipped`
names what the chosen environment left out, so a green `make ci`
never means two different things without saying which.

Two tiers run in one environment only. Both are listed here
because a tier that quietly exists in one place is a tier whose
absence nobody notices:

| Tier | Target | Runs in | Why not the other |
|---|---|---|---|
| Integration | `ci-compose` | compose | Needs Postgres, Redis and OPA reachable as `pgvector`/`redis`/`opa`, which is a compose network. It will run against Kind — point `LANGGRAPH_API_URL` at a port-forward, the target prints the command — but it is not what `ENV=kind` runs |
| Cluster | `ci-kind` | Kind | A readiness probe, an ingress rule, an SCC and `enableServiceLinks: false` are things compose has no kubelet to be wrong about |
| Nightly | `make test-nightly` | neither, by hand | Kills and restarts a running stack. In no `make ci` list on purpose |
| Timings | `make timings` | neither, by hand | Measures the `make dev` loop — an edit to a module, then the agent's own "serving again" line. Neither `ENV=` has that loop running, and starting one would measure the start instead. With nothing up it prints `no measurement — is the loop running?` and exits non-zero rather than passing (DX-7) |

### The image each one builds

Not one image, and that is the open half of this. Measured, not
assumed:

| Where | Builds |
|---|---|
| Kind (`make kind`) | `Containerfile`, `--target runtime` |
| CI image (`make ci-image`) | `Containerfile`, `--target ci` |
| compose (`template-agent` service) | `Containerfile` |
| OpenShift (`buildconfig.yaml`) | `Containerfile` |

So compose agrees with production and disagrees with Kind. An
integration test that passes under `ENV=compose` has exercised a
different build from the one `ENV=kind` and the pipeline run.
`tests/unit/test_the_environments_agree.py` pins the four, so a
fifth divergence fails rather than appears. Closing it means
OpenShift and compose moving to `Containerfile --target
runtime`, which is a build change on the production path and
wants its own verification, not a line in this table.

## The security properties, and the tests that hold them

These are asserted by `tests/unit/test_workflow_security.py`
rather than by review, because a reviewer who approves fifty
workflow changes approves the fifty-first:

- Every workflow declares `permissions:`. A workflow that omits
  it inherits whatever the repository default is, which is
  usually more than it needs.
- No workflow uses `pull_request_target`. It runs with the base
  repository's secrets against a fork's code, which is the one
  trigger that turns a pull request into a credential.
- A fork-triggered workflow reads no secret.
- Actions are pinned by commit SHA, not by tag. A tag moves.

## A flaky test

`tests/quarantine.yaml`, and nothing else. `@pytest.mark.skip` is
a blanket skip with no owner and no end:

```yaml
quarantined:
  - test: tests/unit/foo/test_bar.py::TestBaz::test_sometimes
    owner: ada
    until: 2026-11-30
    reason: races with the Redis fixture about one run in fifty
```

Three fields are required and one test per entry — a pattern
would quarantine a directory. **An expired entry fails the
build**, so at the deadline somebody either fixes the test or
comes back and says out loud that it is being extended. The file
ships empty, and that is the intended state.

## When the pipeline and your laptop disagree

Usually a version: the pipeline runs in the CI image, your
laptop runs whatever is installed. `make doctor` prints what it
found and what it expected. The remaining causes, in the order
they happen: a stale `.venv` after a dependency change, a test
that depends on another test's leftovers (run it alone), and a
service the job declares that is not running locally
(`podman compose up`).
