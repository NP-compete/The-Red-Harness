# Tests

Three folders. The rule is what each holds, not what kind of test
it is — that is what markers are for.

| | |
|---|---|
| `unit/` | every test, mirroring the source tree |
| `fixtures/` | what the tests read: config trees, cassettes, helpers, mock servers |
| `load/` | k6 scripts — a different runner, not pytest |

There were thirteen folders here. `contracts/`, `integration/`,
`nightly/` and `skills/` all held tests that a marker already
described, and the folder was the half nobody ran: `contracts/` and
`integration/` were in no CI job at all, and two of their tests had
been failing while nine others pointed at a port nothing listens on.
A marker and a directory saying the same thing is one of them too
many.

## Running them

```sh
make test              # everything except the two markers below
make test-integration  # -m integration, a slice of the above
make test-skills       # -m skills — real model calls, costs money
make test-nightly      # -m nightly — needs a running stack
make coverage          # the same suite, with the floor enforced
make load-smoke        # the k6 scripts, against a running agent
```

`make test` is one pytest invocation over `tests/`. Anything added
under here runs without being wired up anywhere.

## Markers

| marker | meaning |
|---|---|
| `integration` | several components together; still hermetic |
| `e2e` | needs a running agent — **skips** when none answers |
| `slow` | over 30 seconds |
| `contract` | pins a cross-repo or cross-version interface |
| `skills` | grades real model output |
| `nightly` | needs a Kind or OpenShift stack |
| `real_datastores` | opts out of the conftest that points Redis and Postgres at a dead port |

`make test` deselects `skills` and `nightly` — the only two that cost
money or need a cluster. Both are named by `make ci-skipped`, because
a check that is quietly absent reads exactly like a check that passed.

Anything needing a server should **skip**, not fail: a red suite that
only means "nothing running here" is one people learn to ignore.
`unit/aegra/test_e2e.py` shows the shape — it probes `/health` and
skips with the address it tried.

## What CI runs

A PR runs `test.yml`: sixteen `make <target>` steps, including
`make coverage`, plus `make pre-commit`. Every step is a Makefile
target so the pipeline and a laptop cannot disagree —
`make workflow-steps` enforces that, and `unit/test_ci_is_one_list.py`
checks the two lists still match.

## Two things that keep this shape

- `unit/test_every_suite_runs_somewhere.py` — `tests/` holds exactly
  these three folders, `make test` takes all of `tests/`, and each
  deselected marker still **collects** something. That last one
  matters: `-m skills` once collected zero because a path broke, and a
  grep for the marker could not tell the difference.
- `unit/test_the_suite_does_not_edit_the_tree_it_ships.py` — no test
  writes to a path under `config_root()`. One fixture used to edit the
  real `config/agent/runtime/agent.yaml` and restore it on teardown,
  which holds until a run is interrupted. Copy to `tmp_path` and point
  `CONFIG_PATH` *and* the loader's `_base_dir` at the copy.

## Not in here

- `scripts/bench/` — standalone latency benchmarks, stdlib only.
- `.local/skill-runs/` — where `make test-skills` writes its output.
